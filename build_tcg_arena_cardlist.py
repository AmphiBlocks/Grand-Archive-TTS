import argparse
import json
import subprocess
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode


API_BASE = "https://api.gatcg.com"
SEARCH_URL = f"{API_BASE}/cards/search"
FEATURED_SETS_URL = f"{API_BASE}/featured-sets"
PAGE_SIZE = 96
DEFAULT_IMAGE_DIR = "card_images/grand_archive"
DEFAULT_OUTPUT = "TCG_Arena_Cardlist.json"

# Featured sets do not include every supplemental/promo prefix.
EXTRA_PREFIXES = [
    "DOA 1st",
    "DOAp",
    "DOASD",
    "DOA Alter",
    "FTC",
    "FTCA",
    "ALC",
    "ALCSD",
    "ALC Alter",
    "MRC",
    "MRC 1st",
    "MRC Alter",
    "ReC-SHD",
    "ReC-SLM",
    "AMB",
    "AMBSD",
    "AMB 1st",
    "AMB Alter",
    "ReC-HVF",
    "ReC-IDY",
    "HVN",
    "HVN 1st",
    "DTRSD",
    "DTR",
    "DTR 1st",
    "ReC-BRV",
    "PTM",
    "PTM 1st",
    "PTMLGS",
    "P24",
]


def run_command(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}")
    return proc.stdout


def fetch_json(url, params=None):
    full_url = url
    if params:
        full_url = f"{url}?{urlencode(params, doseq=True)}"
    output = run_command(["curl", "-s", full_url])
    return json.loads(output)


def fetch_binary(url, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    run_command(["curl", "-s", "-L", url, "-o", str(destination)])


def first_nonempty(*values):
    for value in values:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
        elif value is not None:
            return value
    return ""


def parse_date(value):
    if not value:
        return datetime.max
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def discover_prefixes():
    payload = fetch_json(FEATURED_SETS_URL)
    ordered = []
    seen = set()
    for featured in sorted(payload, key=lambda row: parse_date(min((s.get("release_date") for s in row.get("sets", [])), default=None))):
        for set_row in sorted(featured.get("sets", []), key=lambda row: (parse_date(row.get("release_date")), row.get("prefix") or "")):
            prefix = (set_row.get("prefix") or "").strip()
            if prefix and prefix not in seen:
                seen.add(prefix)
                ordered.append(prefix)
    for prefix in EXTRA_PREFIXES:
        if prefix not in seen:
            seen.add(prefix)
            ordered.append(prefix)
    return ordered


def remote_image_base():
    remote = run_command(["git", "remote", "get-url", "origin"]).strip()
    branch = run_command(["git", "branch", "--show-current"]).strip()
    remote = remote.removesuffix(".git")
    if remote.startswith("git@github.com:"):
        remote = remote.replace("git@github.com:", "https://github.com/")
    if not remote.startswith("https://github.com/"):
        raise RuntimeError(f"Unsupported git remote for GitHub raw URL generation: {remote}")
    owner_repo = remote.removeprefix("https://github.com/").strip("/")
    return f"https://raw.githubusercontent.com/{owner_repo}/{branch}"


def cost_value(card):
    cost = card.get("cost") or {}
    value = cost.get("value")
    if value is None:
        value = card.get("cost_memory")
    if value is None:
        value = card.get("cost_reserve")
    if value is None:
        return 0
    return value


def record_cost_value(record):
    cost = (record or {}).get("cost") or {}
    value = cost.get("value")
    if value is None:
        value = (record or {}).get("cost_memory")
    if value is None:
        value = (record or {}).get("cost_reserve")
    if value is None:
        return 0
    return value


def normalize_types(types):
    if not types:
        return ""
    return " / ".join(str(value) for value in types if value)


def is_horizontal(orientation_value):
    return str(orientation_value or "").lower() == "horizontal"


def preferred_edition(card):
    editions = (card.get("result_editions") or []) or (card.get("editions") or [])
    if editions:
        return editions[0]
    return {}


def back_orientation(card):
    editions = (card.get("result_editions") or []) or (card.get("editions") or [])
    for edition in editions:
        others = edition.get("other_orientations") or []
        if others:
            return others[0]
    return None


def image_extension(image_path: str):
    suffix = Path((image_path or "").split("?", 1)[0]).suffix.lower()
    return suffix or ".jpg"


def local_image_path(image_dir: Path, image_uuid: str, image_path: str):
    ext = image_extension(image_path)
    return image_dir / f"{image_uuid}{ext}"


def image_url_for_repo(base_url: str, repo_root: Path, path: Path):
    rel = path.relative_to(repo_root).as_posix()
    return f"{base_url}/{rel}"


def card_face(name, types, cost, image, orientation):
    return {
        "name": name,
        "type": normalize_types(types),
        "cost": cost,
        "image": image,
        "isHorizontal": is_horizontal(orientation),
    }


def is_token(card):
    return any(str(card_type).upper() == "TOKEN" for card_type in (card.get("types") or []))


def build_entry(card, front_image_url, back_image_url=None):
    entry = OrderedDict()
    entry["id"] = card["uuid"]
    entry["isToken"] = is_token(card)

    faces = OrderedDict()
    front_edition = preferred_edition(card)
    faces["front"] = card_face(
        card.get("name") or "",
        card.get("types") or [],
        cost_value(card),
        front_image_url,
        front_edition.get("orientation"),
    )

    back = back_orientation(card)
    if back:
        back_edition = back.get("edition") or {}
        faces["back"] = card_face(
            back.get("name") or card.get("name") or "",
            back.get("types") or card.get("types") or [],
            record_cost_value(back),
            back_image_url or "",
            first_nonempty(back_edition.get("orientation"), back.get("orientation")),
        )

    entry["face"] = faces
    entry["name"] = card.get("name") or ""
    entry["type"] = normalize_types(card.get("types") or [])
    entry["cost"] = cost_value(card)
    return entry


def fetch_cards(prefix, limit_remaining=None):
    page = 1
    cards = []
    while True:
        payload = fetch_json(
            SEARCH_URL,
            {
                "prefix": prefix,
                "page": page,
                "page_size": PAGE_SIZE,
            },
        )
        page_cards = payload.get("data") or []
        cards.extend(page_cards)
        has_more = bool(payload.get("has_more"))
        if not has_more:
            break
        if limit_remaining is not None and len(cards) >= limit_remaining:
            break
        page += 1
    return cards


def export_cards(limit, output_path: Path, image_dir: Path, image_base_url: str, repo_root: Path):
    card_map = OrderedDict()
    downloaded = {}
    prefixes = discover_prefixes()

    for prefix in prefixes:
        if limit is not None and len(card_map) >= limit:
            break
        needed = None if limit is None else max(limit - len(card_map), 1)
        for card in fetch_cards(prefix, limit_remaining=needed):
            card_uuid = card.get("uuid")
            if not card_uuid or card_uuid in card_map:
                continue

            front_edition = preferred_edition(card)
            front_image_path = first_nonempty(front_edition.get("image"))
            if not front_image_path:
                continue
            front_uuid = first_nonempty(front_edition.get("uuid"), card_uuid)
            front_local_path = local_image_path(image_dir, front_uuid, front_image_path)
            if front_image_path not in downloaded:
                fetch_binary(f"{API_BASE}{front_image_path}", front_local_path)
                downloaded[front_image_path] = front_local_path
            else:
                front_local_path = downloaded[front_image_path]

            back = back_orientation(card)
            back_repo_url = None
            if back:
                back_edition = back.get("edition") or {}
                back_image_path = first_nonempty(back.get("image"), back_edition.get("image"))
                if back_image_path:
                    back_uuid = first_nonempty(back_edition.get("uuid"), back.get("uuid"), f"{card_uuid}_back")
                    back_local_path = local_image_path(image_dir, back_uuid, back_image_path)
                    if back_image_path not in downloaded:
                        fetch_binary(f"{API_BASE}{back_image_path}", back_local_path)
                        downloaded[back_image_path] = back_local_path
                    else:
                        back_local_path = downloaded[back_image_path]
                    back_repo_url = image_url_for_repo(image_base_url, repo_root, back_local_path)

            front_repo_url = image_url_for_repo(image_base_url, repo_root, front_local_path)
            card_map[card_uuid] = build_entry(card, front_repo_url, back_repo_url)

            if limit is not None and len(card_map) >= limit:
                break

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(card_map, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return {
        "cards": len(card_map),
        "images": len({path.resolve() for path in downloaded.values()}),
        "prefixes_scanned": prefixes,
    }


def main():
    parser = argparse.ArgumentParser(description="Build TCG Arena card list JSON from Grand Archive API.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum unique cards to export.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path.")
    parser.add_argument("--image-dir", default=DEFAULT_IMAGE_DIR, help="Repo-relative image output directory.")
    parser.add_argument("--image-base-url", default="", help="Base URL prefix for emitted image URLs.")
    args = parser.parse_args()

    repo_root = Path.cwd()
    output_path = repo_root / args.output
    image_dir = repo_root / args.image_dir
    image_base_url = args.image_base_url.strip() or remote_image_base()

    result = export_cards(args.limit, output_path, image_dir, image_base_url.rstrip("/"), repo_root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
