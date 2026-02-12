import argparse
import datetime as dt
import time
from collections import defaultdict

import requests


API_DEFAULT = "https://api.gatcg.com/cards/search"

COLLATION_SPECS = [
    {
        "id": "PHANTOM_MONARCHS",
        "collation_name": "PHANTOM_MONARCHS_8_CARD",
        "set_names": ["Phantom Monarchs", "Phantom Monarchs First Edition"],
    },
    {
        "id": "HVN",
        "collation_name": "HVN_8_CARD",
        "set_names": ["Abyssal Heaven", "Abyssal Heaven First Edition"],
    },
]

RARITY_ID_TO_KEY = {
    1: "COMMON",
    2: "UNCOMMON",
    3: "RARE",
    4: "SUPER_RARE",
    5: "ULTRA_RARE",
    6: "UR_ALT",
    7: "CSR",
    8: "CUR",
    9: "PROMO",
}

POOL_ORDER = [
    "COMMON",
    "UNCOMMON",
    "RARE",
    "SUPER_RARE",
    "ULTRA_RARE",
    "CSR",
    "CUR",
    "TOKEN",
    "TOKEN_OR_COMMON_CHAMPION",
    "FOIL_ANY",
]


def lua_quote(value: str) -> str:
    value = "" if value is None else str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    value = value.replace('"', '\\"')
    return f'"{value}"'


def lua_list_str(values):
    return "{ " + ", ".join(lua_quote(v) for v in values) + " }"


def sort_uuid_rows(rows):
    return sorted(rows, key=lambda r: (r["slug"], r["uuid"]))


def get_page(api: str, page: int, retries: int, timeout: int):
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(api, params={"page": page}, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            print(f"[warn] page {page} -> HTTP {response.status_code} (attempt {attempt})")
        except requests.RequestException as exc:
            print(f"[warn] page {page} -> {exc} (attempt {attempt})")
        time.sleep(0.5 * attempt)
    raise RuntimeError(f"Failed to fetch page {page} after {retries} attempts")


def card_types(card):
    return [str(t) for t in (card.get("types") or [])]


def to_rarity_key(rarity_id):
    return RARITY_ID_TO_KEY.get(rarity_id, f"RARITY_{rarity_id}")


def first_nonempty(*values):
    for v in values:
        if isinstance(v, str):
            s = v.strip()
            if s:
                return s
    return ""


def image_from_record(card, edition):
    ed_images = edition.get("images") if isinstance(edition, dict) else None
    card_images = card.get("images") if isinstance(card, dict) else None
    return first_nonempty(
        (edition or {}).get("image"),
        (edition or {}).get("image_url"),
        (ed_images or {}).get("raw") if isinstance(ed_images, dict) else "",
        (ed_images or {}).get("default") if isinstance(ed_images, dict) else "",
        (ed_images or {}).get("full") if isinstance(ed_images, dict) else "",
        (card or {}).get("image"),
        (card or {}).get("image_url"),
        (card_images or {}).get("raw") if isinstance(card_images, dict) else "",
        (card_images or {}).get("default") if isinstance(card_images, dict) else "",
        (card_images or {}).get("full") if isinstance(card_images, dict) else "",
    )


def pool_key(collation_id, pool_name):
    return f"{collation_id}__{pool_name}"


def output_pool_block(lines, key_name, rows):
    lines.append(f'    ["{key_name}"] = {{')
    for row in sort_uuid_rows(rows):
        lines.append(f'      "{row["uuid"]}", -- {row["slug"]} | {row["name"]} | {row["set_name"]}')
    lines.append("    },")


def output_card_map_block(lines, rows):
    by_uuid = {}
    for row in rows:
        by_uuid[row["uuid"]] = row
    lines.append("  cards = {")
    for uuid in sorted(by_uuid.keys()):
        row = by_uuid[uuid]
        lines.append(f'    ["{uuid}"] = {{')
        lines.append(f'      uuid = "{uuid}",')
        lines.append(f'      slug = {lua_quote(row["slug"])},')
        lines.append(f'      name = {lua_quote(row["name"])},')
        lines.append(f'      image = {lua_quote(row.get("image") or "")},')
        lines.append("      types = { " + ", ".join(lua_quote(t) for t in row["types"]) + " },")
        lines.append("    },")
    lines.append("  },")


def add_collation_block(lines, spec):
    cid = spec["id"]
    cname = spec["collation_name"]
    lines.append(f'    ["{cname}"] = {{')
    lines.append("      slots = {")
    lines.append(
        f'        {{ name = "RARE_PLUS_SLOT", weighted = {{ {{ pool = "{pool_key(cid, "RARE")}", weight = 18 }}, {{ pool = "{pool_key(cid, "SUPER_RARE")}", weight = 5 }}, {{ pool = "{pool_key(cid, "ULTRA_RARE")}", weight = 1 }} }} }},'
    )
    lines.append(f'        {{ name = "UNCOMMON_SLOT_1", pool = "{pool_key(cid, "UNCOMMON")}" }},')
    lines.append(f'        {{ name = "UNCOMMON_SLOT_2", pool = "{pool_key(cid, "UNCOMMON")}" }},')
    lines.append(
        f'        {{ name = "FOIL_SLOT", weighted = {{ {{ pool = "{pool_key(cid, "RARE")}", weight = 45 }}, {{ pool = "{pool_key(cid, "CSR")}", weight = 1 }}, {{ pool = "{pool_key(cid, "SUPER_RARE")}", weight = 36 }}, {{ pool = "{pool_key(cid, "UNCOMMON")}", weight = 90 }}, {{ pool = "{pool_key(cid, "COMMON")}", weight = 188 }} }} }},'
    )
    lines.append(f'        {{ name = "COMMON_SLOT_1", pool = "{pool_key(cid, "COMMON")}" }},')
    lines.append(f'        {{ name = "COMMON_SLOT_2", pool = "{pool_key(cid, "COMMON")}" }},')
    lines.append(f'        {{ name = "COMMON_SLOT_3", pool = "{pool_key(cid, "COMMON")}" }},')
    lines.append(f'        {{ name = "TOKEN_SLOT", pool = "{pool_key(cid, "TOKEN_OR_COMMON_CHAMPION")}" }},')
    lines.append("      },")
    lines.append("    },")


def main():
    parser = argparse.ArgumentParser(
        description="Build GA collation data grouped by rarity for PTM + Abyssal Heaven."
    )
    parser.add_argument("--api", default=API_DEFAULT, help="GATCG cards/search endpoint")
    parser.add_argument(
        "--out",
        default="out_lua/collation/ga_collation_phantom_monarchs.lua",
        help="Output Lua file path",
    )
    parser.add_argument("--sleep", type=float, default=0.1, help="Delay per page")
    parser.add_argument("--retries", type=int, default=3, help="Request retries")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout seconds")
    args = parser.parse_args()

    all_target_set_names = sorted({n for spec in COLLATION_SPECS for n in spec["set_names"]})
    set_to_collation_ids = defaultdict(list)
    for spec in COLLATION_SPECS:
        for n in spec["set_names"]:
            set_to_collation_ids[n].append(spec["id"])

    first = get_page(args.api, 1, args.retries, args.timeout)
    total_pages = int(first.get("total_pages") or 1)
    print(f"Total pages reported: {total_pages}")

    pools_by_collation = {
        spec["id"]: defaultdict(list)
        for spec in COLLATION_SPECS
    }

    all_rows = []

    def ingest_page(payload):
        for card in payload.get("data") or []:
            types = card_types(card)
            is_token = "TOKEN" in types
            is_common_champion = "CHAMPION" in types
            card_name = card.get("name") or card.get("title") or ""

            for edition in card.get("editions") or []:
                set_name = ((edition.get("set") or {}).get("name") or "").strip()
                if set_name not in set_to_collation_ids:
                    continue

                uuid = (edition.get("uuid") or card.get("uuid") or "").strip()
                slug = (card.get("slug") or edition.get("slug") or "").strip()
                rarity_id = edition.get("rarity")
                rarity_key = to_rarity_key(rarity_id)
                if not uuid or not slug:
                    continue

                row = {
                    "uuid": uuid,
                    "slug": slug,
                    "name": card_name,
                    "set_name": set_name,
                    "rarity_id": rarity_id,
                    "rarity_key": rarity_key,
                    "types": sorted(types),
                    "image": image_from_record(card, edition),
                }

                all_rows.append(row)

                for collation_id in set_to_collation_ids[set_name]:
                    pools = pools_by_collation[collation_id]
                    pools[rarity_key].append(row)
                    pools["FOIL_ANY"].append(row)
                    if is_token:
                        pools["TOKEN"].append(row)
                    if is_token or (rarity_key == "COMMON" and is_common_champion):
                        pools["TOKEN_OR_COMMON_CHAMPION"].append(row)

    ingest_page(first)
    for page in range(2, total_pages + 1):
        time.sleep(args.sleep)
        data = get_page(args.api, page, args.retries, args.timeout)
        ingest_page(data)
        if page % 5 == 0 or page == total_pages:
            print(f"Fetched page {page}/{total_pages}")

    # Deduplicate per-collation pools by UUID.
    for spec in COLLATION_SPECS:
        cid = spec["id"]
        pools = pools_by_collation[cid]
        for key in list(pools.keys()):
            unique = {}
            for row in pools[key]:
                unique[row["uuid"]] = row
            pools[key] = list(unique.values())

    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    lines = []
    lines.append("-- Auto-generated GA collation data")
    lines.append("-- Source: api.gatcg.com/cards/search")
    lines.append("-- Set filter: " + ", ".join(all_target_set_names))
    lines.append(f"-- Generated: {generated_at}")
    lines.append("")
    lines.append("local M = {")
    lines.append("  meta = {")
    lines.append(f"    generated_at = {lua_quote(generated_at)},")
    lines.append(f"    source_api = {lua_quote(args.api)},")
    lines.append(f"    set_names = {lua_list_str(all_target_set_names)},")
    lines.append("  },")
    output_card_map_block(lines, all_rows)
    lines.append("  pools = {")
    for spec in COLLATION_SPECS:
        cid = spec["id"]
        pools = pools_by_collation[cid]
        for pool_name in POOL_ORDER:
            output_pool_block(lines, pool_key(cid, pool_name), pools.get(pool_name, []))
    lines.append("  },")
    lines.append('  collations = {')
    for spec in COLLATION_SPECS:
        add_collation_block(lines, spec)
    lines.append("  },")
    lines.append("}")
    lines.append('M.collations["ABYSSAL_HEAVEN_8_CARD"] = M.collations["HVN_8_CARD"]')
    lines.append("")
    lines.append("function getMap() return M end")
    lines.append("")
    lines.append("function getCardData(params)")
    lines.append("  params = params or {}")
    lines.append('  local uuid = params["uuid"]')
    lines.append("  if not uuid then return nil end")
    lines.append("  local card = M.cards[uuid]")
    lines.append("  if not card then return nil end")
    lines.append("  return {")
    lines.append("    name = card.name,")
    lines.append("    image = card.image,")
    lines.append("    uuid = card.uuid,")
    lines.append("    slug = card.slug,")
    lines.append("    types = card.types,")
    lines.append("  }")
    lines.append("end")
    lines.append("")
    lines.append("local function randomFromPool(pool, used)")
    lines.append("  if not pool or #pool == 0 then return nil end")
    lines.append("  local attempts = 0")
    lines.append("  while attempts < 50 do")
    lines.append("    local card = pool[math.random(#pool)]")
    lines.append("    if not used[card] then")
    lines.append("      return card")
    lines.append("    end")
    lines.append("    attempts = attempts + 1")
    lines.append("  end")
    lines.append("  return nil")
    lines.append("end")
    lines.append("")
    lines.append("local function weightedRoll(weighted, used)")
    lines.append("  if not weighted or #weighted == 0 then return nil end")
    lines.append("  local total = 0")
    lines.append("  for _, entry in ipairs(weighted) do")
    lines.append("    total = total + (entry.weight or 0)")
    lines.append("  end")
    lines.append("  if total <= 0 then return nil end")
    lines.append("")
    lines.append("  local attempts = 0")
    lines.append("  while attempts < 50 do")
    lines.append("    local roll = math.random() * total")
    lines.append("    local running = 0")
    lines.append("    for _, entry in ipairs(weighted) do")
    lines.append("      running = running + (entry.weight or 0)")
    lines.append("      if roll <= running then")
    lines.append("        local pool = M.pools[entry.pool]")
    lines.append("        local card = randomFromPool(pool, used)")
    lines.append("        if card then return card end")
    lines.append("        break")
    lines.append("      end")
    lines.append("    end")
    lines.append("    attempts = attempts + 1")
    lines.append("  end")
    lines.append("  return nil")
    lines.append("end")
    lines.append("")
    lines.append("function getPool(params)")
    lines.append('  local pools = M["pools"]')
    lines.append('  return pools and pools[params["pool"]]')
    lines.append("end")
    lines.append("")
    lines.append("function getCollation(params)")
    lines.append('  return M["collations"][params["name"]]')
    lines.append("end")
    lines.append("")
    lines.append("function GeneratePack(params)")
    lines.append("  params = params or {}")
    lines.append('  local collationName = params.collation_name or "PHANTOM_MONARCHS_8_CARD"')
    lines.append("  local collation = M.collations[collationName]")
    lines.append("  if not collation then")
    lines.append("    print(\"Unknown collation:\", collationName)")
    lines.append("    return {}")
    lines.append("  end")
    lines.append("")
    lines.append("  local used = {}")
    lines.append("  local cards = {}")
    lines.append("  for _, slot in ipairs(collation.slots or {}) do")
    lines.append("    local card = nil")
    lines.append("    if slot.weighted then")
    lines.append("      card = weightedRoll(slot.weighted, used)")
    lines.append("    elseif slot.pool then")
    lines.append("      card = randomFromPool(M.pools[slot.pool], used)")
    lines.append("    end")
    lines.append("    if card then")
    lines.append("      used[card] = true")
    lines.append("      table.insert(cards, card)")
    lines.append("    end")
    lines.append("  end")
    lines.append("  return cards")
    lines.append("end")
    lines.append("")
    lines.append("function onLoad(saved_data)")
    lines.append("  Global.setVar('GA_CollationData', self)")
    lines.append("  Global.setVar('GA_CollationLibrary', self)")
    lines.append("end")
    lines.append("")

    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print("Done.")
    print(f"Wrote: {args.out}")
    for spec in COLLATION_SPECS:
        cid = spec["id"]
        cname = spec["collation_name"]
        pools = pools_by_collation[cid]
        print(f"Pool sizes for {cname}:")
        for pool_name in POOL_ORDER:
            print(f"  {pool_name}: {len(pools.get(pool_name, []))}")


if __name__ == "__main__":
    main()
