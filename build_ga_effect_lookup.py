import argparse
import json
import re
import time
from collections import defaultdict

import requests

API_DEFAULT = "https://api.gatcg.com/cards/search"


def reduced_slug_from_title(name: str, side: str = None) -> str:
    name = name or ""
    # left half before '/' if double-sided title
    m = re.match(r"^\s*(.*?)\s*/\s*.*$", name)
    base = m.group(1) if m else name
    slug = base.lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[',]", "", slug)
    slug = re.sub(r"[^0-9a-z\-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if side in ("front", "back"):
        slug = f"{slug}/{side}"
    return slug


def lua_long_bracket(s: str) -> str:
    """
    Safely wrap arbitrary text in Lua long brackets, choosing a level that
    does not appear in the string (e.g., [=[ ... ]=], [==[ ... ]==], ...).
    """
    s = "" if s is None else str(s)
    for eqs in range(0, 6):
        left = "[" + ("=" * eqs) + "["
        right = "]" + ("=" * eqs) + "]"
        if (left not in s) and (right not in s):
            return f"{left}{s}{right}"
    s = s.replace("]", "]]")
    return f"[{s}]"


def lua_string(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\\", "\\\\")
    s = s.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    s = s.replace('"', '\\"')
    return f"\"{s}\""


def lua_list(items):
    items = items or []
    return "{ " + ", ".join(lua_string(x) for x in items) + " }"


def coalesce(*values):
    for v in values:
        if v:
            return v
    return ""


def pick_uuid(card: dict, orientation: dict = None) -> str:
    if orientation:
        return coalesce(
            orientation.get("uuid"),
            (orientation.get("edition") or {}).get("uuid"),
            card.get("default_uuid"),
            card.get("uuid"),
            _first_edition_uuid(card),
        )
    return coalesce(
        card.get("default_uuid"),
        card.get("uuid"),
        _first_edition_uuid(card),
    )


def _first_edition_uuid(card: dict) -> str:
    for ed in (card.get("editions") or []):
        uuid = ed.get("uuid")
        if uuid:
            return uuid
    for ed in (card.get("result_editions") or []):
        uuid = ed.get("uuid")
        if uuid:
            return uuid
    return ""


def is_token(card: dict) -> bool:
    types = card.get("types") or []
    return any(t == "TOKEN" for t in types)


def home_deck_for(card: dict) -> str:
    if is_token(card):
        return "none"
    cost = card.get("cost") or {}
    cost_type = (cost.get("type") or "").lower()
    if cost_type == "memory":
        return "material"
    if cost_type == "reserve":
        return "main"
    return "none"


def extract_records(card: dict):
    records = []

    # Front / default
    front_name = card.get("name") or card.get("title") or ""
    front_effect = (card.get("effect_raw") or card.get("effect") or "").strip()
    home_deck = home_deck_for(card)
    types = card.get("types") or []
    subtypes = card.get("subtypes") or []
    records.append(
        {
            "name": front_name,
            "side": "front",
            "effect_raw": front_effect,
            "uuid": pick_uuid(card),
            "home_deck": home_deck,
            "types": types,
            "subtypes": subtypes,
        }
    )

    seen_slugs = set()

    def add_orients(seq):
        if not isinstance(seq, list):
            return
        for o in seq:
            if not isinstance(o, dict):
                continue
            slug = o.get("slug") or ""
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            name = o.get("name") or front_name
            text = o.get("effect_raw") or (o.get("edition") or {}).get("effect_raw") or ""
            records.append(
                {
                    "name": name,
                    "side": "back",
                    "effect_raw": text.strip(),
                    "uuid": pick_uuid(card, o),
                    "home_deck": home_deck,
                    "types": types,
                    "subtypes": subtypes,
                }
            )

    for ed in (card.get("editions") or []):
        add_orients(ed.get("other_orientations"))
    for ed in (card.get("result_editions") or []):
        add_orients(ed.get("other_orientations"))

    return records


def get_page(api: str, page: int, retries: int, timeout: int):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(api, params={"page": page}, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            print(f"[warn] page {page} -> HTTP {r.status_code} (attempt {attempt})")
        except requests.RequestException as exc:
            print(f"[warn] page {page} -> {exc} (attempt {attempt})")
        time.sleep(0.5 * attempt)
    raise RuntimeError(f"Failed to fetch page {page} after {retries} attempts")


def prefer_entry(existing: dict, incoming: dict) -> dict:
    if not existing:
        return incoming
    if not existing.get("effect") and incoming.get("effect"):
        return incoming
    if not existing.get("default-uuid") and incoming.get("default-uuid"):
        return incoming
    if not existing.get("home_deck") and incoming.get("home_deck"):
        return incoming
    if not existing.get("types") and incoming.get("types"):
        return incoming
    if not existing.get("subtypes") and incoming.get("subtypes"):
        return incoming
    return existing


def main():
    parser = argparse.ArgumentParser(
        description="Build GA effect lookup table with name, default-uuid, and effect."
    )
    parser.add_argument("--api", default=API_DEFAULT, help="GATCG cards/search endpoint")
    parser.add_argument("--out", default="ga_effects_all.lua", help="Output Lua file")
    parser.add_argument("--sleep", type=float, default=0.1, help="Delay per page")
    parser.add_argument("--retries", type=int, default=3, help="Request retries")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout (seconds)")
    args = parser.parse_args()

    first = get_page(args.api, 1, args.retries, args.timeout)
    total_pages = int(first.get("total_pages") or 1)
    print(f"Total pages reported: {total_pages}")

    lookup = {}

    for c in (first.get("data") or []):
        for r in extract_records(c):
            name = (r.get("name") or "").strip()
            if not name:
                continue
            slug = reduced_slug_from_title(name, None)
            if not slug:
                continue
            entry = {
                "name": name,
                "default-uuid": r.get("uuid") or "",
                "effect": r.get("effect_raw") or "",
                "home_deck": r.get("home_deck") or "none",
                "types": r.get("types") or [],
                "subtypes": r.get("subtypes") or [],
            }
            lookup[slug] = prefer_entry(lookup.get(slug), entry)

    for page in range(2, total_pages + 1):
        time.sleep(args.sleep)
        j = get_page(args.api, page, args.retries, args.timeout)
        for c in (j.get("data") or []):
            for r in extract_records(c):
                name = (r.get("name") or "").strip()
                if not name:
                    continue
                slug = reduced_slug_from_title(name, None)
                if not slug:
                    continue
                entry = {
                    "name": name,
                    "default-uuid": r.get("uuid") or "",
                    "effect": r.get("effect_raw") or "",
                    "home_deck": r.get("home_deck") or "none",
                    "types": r.get("types") or [],
                    "subtypes": r.get("subtypes") or [],
                }
                lookup[slug] = prefer_entry(lookup.get(slug), entry)
        print(f"Fetched page {page}/{total_pages} (rows so far: {len(lookup)})")

    lines = []
    lines.append("-- Auto-generated GA effect lookup table")
    lines.append("-- Keys are reduced title slugs (and /front or /back for double-sided)")
    lines.append("local M = {")

    for slug in sorted(lookup.keys()):
        entry = lookup[slug]
        name = lua_string(entry.get("name"))
        uuid = lua_string(entry.get("default-uuid"))
        home_deck = lua_string(entry.get("home_deck"))
        types = lua_list(entry.get("types"))
        subtypes = lua_list(entry.get("subtypes"))
        effect = lua_long_bracket(entry.get("effect"))
        lines.append(
            f'  ["{slug}"] = {{ ["name"] = {name}, ["default-uuid"] = {uuid}, ["home_deck"] = {home_deck}, ["types"] = {types}, ["subtypes"] = {subtypes}, ["effect"] = {effect} }},'
        )

    lines.append("}")
    lines.append("")
    lines.append("function getMap() return M end")
    lines.append("")
    lines.append("function getEntry(params)")
    lines.append('  return M[params["slug"]]')
    lines.append("end")
    lines.append("")
    lines.append("function getRawEffect(params)")
    lines.append('  local e = M[params["slug"]]')
    lines.append('  return e and e["effect"]')
    lines.append("end")
    lines.append("")
    lines.append("function onLoad(saved_data)")
    lines.append("  Global.setVar('GA_EffectLibrary', self)")
    lines.append("end")
    lines.append("")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Done. Wrote {len(lookup)} entries to {args.out}")


if __name__ == "__main__":
    main()
