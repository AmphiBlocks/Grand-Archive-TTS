import argparse
import datetime as dt
import time
from collections import defaultdict

import requests

API_DEFAULT = "https://api.gatcg.com/cards/search"

STANDARD_COLLATIONS = [
    {
        "id": "PHANTOM_MONARCHS",
        "collation_name": "PHANTOM_MONARCHS_8_CARD",
        "set_names": ["Phantom Monarchs", "Phantom Monarchs First Edition"],
        "first_edition_prefix_fallback": "PTM 1st",
        "uncommon_slots": 2,
        "common_slots": 3,
    },
    {
        "id": "HVN",
        "collation_name": "HVN_8_CARD",
        "set_names": ["Abyssal Heaven", "Abyssal Heaven First Edition"],
        "first_edition_prefix_fallback": "HVN 1st",
        "uncommon_slots": 2,
        "common_slots": 3,
    },
    {
        "id": "DTR",
        "collation_name": "DTR_12_CARD",
        "set_prefixes": ["DTR"],
        "first_edition_prefix_fallback": "DTR 1st",
        "uncommon_slots": 3,
        "common_slots": 6,
    },
]

MRC_BASE_SET = "Mercurial Heart"
MRC_FIRST_ED_SET = "Mercurial Heart First Edition"
MRC_ALTER_SET = "Mercurial Heart Alter Edition"

MRC_1E_COLLATION = {"id": "MRC1E", "collation_name": "MRC_1E_8_CARD"}
MRC_ALTER_COLLATION = {"id": "MRCALT", "collation_name": "MRC_ALTER_8_CARD"}

AMB_BASE_PREFIXES = ["AMB"]
AMB_1E_PREFIXES = ["AMB 1st", "AMB+1st"]
AMB_ALTER_PREFIXES = ["AMB Alter", "AMB+Alter"]

AMB_1E_COLLATION = {"id": "AMB1E", "collation_name": "AMB_1E_8_CARD"}
AMB_ALTER_COLLATION = {"id": "AMBALT", "collation_name": "AMB_ALTER_8_CARD"}

ALC_BASE_PREFIXES = ["ALC"]
ALC_ALTER_PREFIXES = ["ALC Alter", "ALC+Alter"]

ALC_COLLATION = {"id": "ALC", "collation_name": "ALC_12_CARD"}
ALC_ALTER_COLLATION = {"id": "ALCALT", "collation_name": "ALC_ALTER_12_CARD"}

FTC_PREFIXES = ["FTC", "FTC 1st", "FTC+1st"]
FTC_COLLATION = {"id": "FTC", "collation_name": "FTC_8_CARD"}

DOA_1E_PREFIXES = ["DOA 1st", "DOA+1st", "DOA"]
DOA_ALTER_PREFIXES = ["DOA Alter", "DOA+Alter", "DOAALTER"]
DOA_1E_COLLATION = {"id": "DOA1E", "collation_name": "DOA_1E_12_CARD"}
DOA_ALTER_COLLATION = {"id": "DOAALT", "collation_name": "DOA_ALTER_12_CARD"}

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

BOOSTER_FALLBACK_RARITIES = {
    "ULTRA_RARE": 5,
    "CSR": 7,
    "CUR": 8,
}


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


def get_page(api: str, page: int, retries: int, timeout: int, params=None):
    query = {"page": page}
    if params:
        query.update(params)
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(api, params=query, timeout=timeout)
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


def normalize_other_orientation(other):
    edition = other.get("edition") if isinstance(other, dict) else None
    if not isinstance(edition, dict):
        edition = {}
    return {
        "name": (other.get("name") or "") if isinstance(other, dict) else "",
        "slug": (other.get("slug") or "") if isinstance(other, dict) else "",
        "uuid": first_nonempty(edition.get("uuid"), (other or {}).get("uuid") if isinstance(other, dict) else ""),
        "image": first_nonempty((other or {}).get("image") if isinstance(other, dict) else "", edition.get("image"), edition.get("image_url")),
        "orientation": first_nonempty(edition.get("orientation"), (other or {}).get("orientation") if isinstance(other, dict) else "", "back"),
        "types": [str(t) for t in ((other.get("types") if isinstance(other, dict) else []) or [])],
    }


def dedupe_rows(rows):
    by_uuid = {}
    for row in rows:
        by_uuid[row["uuid"]] = row
    return list(by_uuid.values())


def prefix_variants(prefix_value):
    variants = []
    for p in [prefix_value, str(prefix_value).replace(" ", "+"), str(prefix_value).replace("+", " ")]:
        p = str(p).strip()
        if p and p not in variants:
            variants.append(p)
    return variants


def normalize_prefix(prefix_value):
    return str(prefix_value or "").strip().replace("+", " ").lower()


def rows_from_payload(
    payload,
    target_set_lookup,
    target_prefix_lookup,
    forced_prefix=None,
    forced_rarity=None,
    bypass_target_filters=False,
):
    rows = []
    for card in payload.get("data") or []:
        types = card_types(card)
        card_name = card.get("name") or card.get("title") or ""
        for edition in card.get("editions") or []:
            set_name = ((edition.get("set") or {}).get("name") or "").strip()
            set_prefix = ((edition.get("set") or {}).get("prefix") or "").strip()
            rarity_id = edition.get("rarity")
            if forced_prefix and set_prefix != forced_prefix:
                continue
            if forced_rarity is not None and rarity_id != forced_rarity:
                continue
            if (not bypass_target_filters) and set_name not in target_set_lookup and set_prefix not in target_prefix_lookup:
                continue

            uuid = first_nonempty(edition.get("uuid"), card.get("uuid"))
            slug = first_nonempty(card.get("slug"), edition.get("slug"))
            if not uuid or not slug:
                continue

            rows.append(
                {
                    "uuid": uuid,
                    "slug": slug,
                    "name": card_name,
                    "set_name": set_name,
                    "set_prefix": set_prefix,
                    "rarity_id": rarity_id,
                    "rarity_key": to_rarity_key(rarity_id),
                    "types": sorted(types),
                    "image": image_from_record(card, edition),
                    "orientation": first_nonempty(edition.get("orientation"), "front"),
                    "orientations": [normalize_other_orientation(o) for o in (edition.get("other_orientations") or [])],
                }
            )
    return rows


def pools_from_rows(rows):
    pools = defaultdict(list)
    for row in rows:
        rarity_key = row["rarity_key"]
        types = row["types"]
        is_token = "TOKEN" in types
        is_common_champion = "CHAMPION" in types

        pools[rarity_key].append(row)
        pools["FOIL_ANY"].append(row)
        if is_token:
            pools["TOKEN"].append(row)
        if is_token or (rarity_key == "COMMON" and is_common_champion):
            pools["TOKEN_OR_COMMON_CHAMPION"].append(row)

    for key in list(pools.keys()):
        pools[key] = dedupe_rows(pools[key])
    return pools


def clone_pools(src):
    out = {}
    for k, rows in src.items():
        out[k] = list(rows)
    return out


def pool_key(collation_id, pool_name):
    return f"{collation_id}__{pool_name}"


def output_pool_block(lines, key_name, rows):
    lines.append(f'    ["{key_name}"] = {{')
    for row in sort_uuid_rows(rows):
        lines.append(f'      "{row["uuid"]}",')
    lines.append("    },")


def output_card_map_block(lines, rows):
    by_uuid = {}
    for row in rows:
        by_uuid[row["uuid"]] = row

    lines.append("  cards = {")
    for uuid in sorted(by_uuid.keys()):
        row = by_uuid[uuid]
        orientations = row.get("orientations") or []
        has_dfc_data = len(orientations) > 0
        lines.append(f'    ["{uuid}"] = {{')
        lines.append(f'      uuid = "{uuid}",')
        lines.append(f'      image = {lua_quote(row.get("image") or "")},')
        if has_dfc_data:
            lines.append('      orientation = "front",')
            lines.append("      orientations = {")
            for alt in orientations:
                lines.append("        {")
                lines.append(f'          uuid = {lua_quote(alt.get("uuid") or "")},')
                lines.append(f'          image = {lua_quote(alt.get("image") or "")},')
                lines.append(f'          orientation = {lua_quote(alt.get("orientation") or "back")},')
                lines.append("        },")
            lines.append("      },")
        lines.append("    },")
    lines.append("  },")


def add_standard_collation_block(lines, collation_id, collation_name, uncommon_slots=2, common_slots=3):
    lines.append(f'    ["{collation_name}"] = {{')
    lines.append("      slots = {")
    lines.append(
        f'        {{ name = "RARE_PLUS_SLOT", weighted = {{ {{ pool = "{pool_key(collation_id, "RARE")}", weight = 18 }}, {{ pool = "{pool_key(collation_id, "SUPER_RARE")}", weight = 5 }}, {{ pool = "{pool_key(collation_id, "ULTRA_RARE")}", weight = 1 }} }} }},'
    )
    for slot_idx in range(1, uncommon_slots + 1):
        lines.append(f'        {{ name = "UNCOMMON_SLOT_{slot_idx}", pool = "{pool_key(collation_id, "UNCOMMON")}" }},')
    lines.append(
        f'        {{ name = "FOIL_SLOT", weighted = {{ {{ pool = "{pool_key(collation_id, "RARE")}", weight = 45 }}, {{ pool = "{pool_key(collation_id, "CSR")}", weight = 1 }}, {{ pool = "{pool_key(collation_id, "SUPER_RARE")}", weight = 36 }}, {{ pool = "{pool_key(collation_id, "UNCOMMON")}", weight = 90 }}, {{ pool = "{pool_key(collation_id, "COMMON")}", weight = 188 }} }} }},'
    )
    for slot_idx in range(1, common_slots + 1):
        lines.append(f'        {{ name = "COMMON_SLOT_{slot_idx}", pool = "{pool_key(collation_id, "COMMON")}" }},')
    lines.append(f'        {{ name = "TOKEN_SLOT", pool = "{pool_key(collation_id, "TOKEN_OR_COMMON_CHAMPION")}" }},')
    lines.append("      },")
    lines.append("    },")


def add_alter_collation_block(lines, collation_id, collation_name, uncommon_slots=2, common_slots=2):
    lines.append(f'    ["{collation_name}"] = {{')
    lines.append("      slots = {")
    lines.append(
        f'        {{ name = "RARE_PLUS_SLOT", weighted = {{ {{ pool = "{pool_key(collation_id, "RARE")}", weight = 18 }}, {{ pool = "{pool_key(collation_id, "SUPER_RARE")}", weight = 5 }}, {{ pool = "{pool_key(collation_id, "ULTRA_RARE")}", weight = 1 }} }} }},'
    )
    lines.append(f'        {{ name = "ALTER_SLOT", pool = "{pool_key(collation_id, "ALTER_EXCLUSIVE")}" }},')
    for slot_idx in range(1, uncommon_slots + 1):
        lines.append(f'        {{ name = "UNCOMMON_SLOT_{slot_idx}", pool = "{pool_key(collation_id, "UNCOMMON")}" }},')
    lines.append(
        f'        {{ name = "FOIL_SLOT", weighted = {{ {{ pool = "{pool_key(collation_id, "RARE")}", weight = 45 }}, {{ pool = "{pool_key(collation_id, "CSR")}", weight = 1 }}, {{ pool = "{pool_key(collation_id, "SUPER_RARE")}", weight = 36 }}, {{ pool = "{pool_key(collation_id, "UNCOMMON")}", weight = 90 }}, {{ pool = "{pool_key(collation_id, "COMMON")}", weight = 188 }} }} }},'
    )
    for slot_idx in range(1, common_slots + 1):
        lines.append(f'        {{ name = "COMMON_SLOT_{slot_idx}", pool = "{pool_key(collation_id, "COMMON")}" }},')
    lines.append(f'        {{ name = "TOKEN_SLOT", pool = "{pool_key(collation_id, "TOKEN_OR_COMMON_CHAMPION")}" }},')
    lines.append("      },")
    lines.append("    },")


def main():
    parser = argparse.ArgumentParser(description="Build GA collation data for multiple sets.")
    parser.add_argument("--api", default=API_DEFAULT, help="GATCG cards/search endpoint")
    parser.add_argument("--out", default="out_lua/collation/ga_collation_phantom_monarchs.lua", help="Output Lua file path")
    parser.add_argument("--sleep", type=float, default=0.1, help="Delay per page")
    parser.add_argument("--retries", type=int, default=3, help="Request retries")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout seconds")
    args = parser.parse_args()

    target_set_names = sorted({
        *[n for spec in STANDARD_COLLATIONS for n in (spec.get("set_names") or [])],
        MRC_BASE_SET,
        MRC_FIRST_ED_SET,
        MRC_ALTER_SET,
    })
    target_set_prefixes = sorted({
        p for spec in STANDARD_COLLATIONS for p in (spec.get("set_prefixes") or [])
    } | set(AMB_BASE_PREFIXES) | set(AMB_1E_PREFIXES) | set(AMB_ALTER_PREFIXES) | set(ALC_BASE_PREFIXES) | set(ALC_ALTER_PREFIXES) | set(FTC_PREFIXES) | set(DOA_1E_PREFIXES) | set(DOA_ALTER_PREFIXES))
    target_set_lookup = set(target_set_names)
    target_prefix_lookup = set(target_set_prefixes)

    first = get_page(args.api, 1, args.retries, args.timeout)
    total_pages = int(first.get("total_pages") or 1)
    print(f"Total pages reported: {total_pages}")

    rows_by_set = defaultdict(list)
    rows_by_prefix = defaultdict(list)

    def ingest_page(payload):
        for row in rows_from_payload(payload, target_set_lookup, target_prefix_lookup):
            rows_by_set[row["set_name"]].append(row)
            rows_by_prefix[normalize_prefix(row["set_prefix"])].append(row)

    ingest_page(first)
    for page in range(2, total_pages + 1):
        time.sleep(args.sleep)
        data = get_page(args.api, page, args.retries, args.timeout)
        ingest_page(data)
        if page % 5 == 0 or page == total_pages:
            print(f"Fetched page {page}/{total_pages}")

    for set_name in list(rows_by_set.keys()):
        rows_by_set[set_name] = dedupe_rows(rows_by_set[set_name])
    for pref in list(rows_by_prefix.keys()):
        rows_by_prefix[pref] = dedupe_rows(rows_by_prefix[pref])

    pools_by_collation = {}
    supplemental_rows_by_collation = defaultdict(list)

    for spec in STANDARD_COLLATIONS:
        cid = spec["id"]
        rows = []
        for set_name in spec.get("set_names") or []:
            rows.extend(rows_by_set.get(set_name, []))
        allowed_prefixes = set(spec.get("set_prefixes") or [])
        if allowed_prefixes:
            for set_name, set_rows in rows_by_set.items():
                del set_name  # key not needed in prefix-filter path
                rows.extend([r for r in set_rows if r["set_prefix"] in allowed_prefixes])
        rows = dedupe_rows(rows)
        pools = pools_from_rows(rows)

        fallback_prefix = spec.get("first_edition_prefix_fallback")
        missing_keys = [k for k in BOOSTER_FALLBACK_RARITIES if len(pools.get(k, [])) == 0]
        if fallback_prefix and missing_keys:
            cards_api = args.api
            print(
                f"[info] {spec['collation_name']}: missing {', '.join(missing_keys)}; "
                f"checking fallback prefix '{fallback_prefix}'"
            )
            for rarity_key in missing_keys:
                rarity_id = BOOSTER_FALLBACK_RARITIES[rarity_key]
                added_rows = []
                for prefix_candidate in prefix_variants(fallback_prefix):
                    try:
                        first_fallback = get_page(
                            cards_api,
                            1,
                            args.retries,
                            args.timeout,
                            {"prefix": prefix_candidate, "rarity": rarity_id},
                        )
                        total_fallback_pages = int(first_fallback.get("total_pages") or 1)
                        fallback_rows = rows_from_payload(
                            first_fallback,
                            target_set_lookup,
                            target_prefix_lookup,
                            forced_rarity=rarity_id,
                            bypass_target_filters=True,
                        )
                        for p in range(2, total_fallback_pages + 1):
                            time.sleep(args.sleep)
                            payload = get_page(
                                cards_api,
                                p,
                                args.retries,
                                args.timeout,
                                {"prefix": prefix_candidate, "rarity": rarity_id},
                            )
                            fallback_rows.extend(
                                rows_from_payload(
                                    payload,
                                    target_set_lookup,
                                    target_prefix_lookup,
                                    forced_rarity=rarity_id,
                                    bypass_target_filters=True,
                                )
                            )
                        fallback_rows = dedupe_rows(fallback_rows)
                        if fallback_rows:
                            added_rows = fallback_rows
                            print(
                                f"[info] {spec['collation_name']}: added {len(fallback_rows)} "
                                f"{rarity_key} rows from prefix '{prefix_candidate}'"
                            )
                            break
                    except Exception as exc:
                        print(
                            f"[warn] fallback query failed for {spec['collation_name']} "
                            f"{rarity_key} prefix '{prefix_candidate}': {exc}"
                        )
                if added_rows:
                    supplemental_rows_by_collation[cid].extend(added_rows)
                else:
                    print(
                        f"[warn] {spec['collation_name']}: no fallback rows found for "
                        f"{rarity_key} using prefix variants of '{fallback_prefix}'"
                    )

        rows.extend(supplemental_rows_by_collation[cid])
        pools_by_collation[cid] = pools_from_rows(dedupe_rows(rows))

    def rows_for_prefixes(prefix_list):
        out = []
        for p in prefix_list:
            out.extend(rows_by_prefix.get(normalize_prefix(p), []))
        return dedupe_rows(out)

    amb_base_rows = rows_for_prefixes(AMB_BASE_PREFIXES)
    amb_1e_rows = rows_for_prefixes(AMB_1E_PREFIXES)
    amb_alt_rows = rows_for_prefixes(AMB_ALTER_PREFIXES)

    amb_base_pools = pools_from_rows(amb_base_rows)

    amb1e_pools = clone_pools(amb_base_pools)
    amb1e_pools["CSR"] = dedupe_rows([r for r in amb_1e_rows if r["rarity_key"] == "CSR"])
    amb1e_cur = dedupe_rows([r for r in amb_1e_rows if r["rarity_key"] == "CUR"])
    if amb1e_cur:
        amb1e_pools["CUR"] = amb1e_cur
    pools_by_collation[AMB_1E_COLLATION["id"]] = amb1e_pools

    ambalt_pools = clone_pools(amb_base_pools)
    ambalt_pools["CSR"] = dedupe_rows([r for r in amb_alt_rows if r["rarity_key"] == "CSR"])
    ambalt_cur = dedupe_rows([r for r in amb_alt_rows if r["rarity_key"] == "CUR"])
    if ambalt_cur:
        ambalt_pools["CUR"] = ambalt_cur
    amb_base_slugs = {r["slug"] for r in amb_base_rows}
    amb_alter_exclusive_rows = [
        r for r in amb_alt_rows
        if r["rarity_key"] != "CSR" and r["slug"] not in amb_base_slugs
    ]
    ambalt_pools["ALTER_EXCLUSIVE"] = dedupe_rows(amb_alter_exclusive_rows)
    pools_by_collation[AMB_ALTER_COLLATION["id"]] = ambalt_pools

    alc_base_rows = rows_for_prefixes(ALC_BASE_PREFIXES)
    alc_alt_rows = rows_for_prefixes(ALC_ALTER_PREFIXES)

    alc_base_pools = pools_from_rows(alc_base_rows)
    pools_by_collation[ALC_COLLATION["id"]] = alc_base_pools

    alcalt_pools = clone_pools(alc_base_pools)
    alcalt_pools["CSR"] = dedupe_rows([r for r in alc_alt_rows if r["rarity_key"] == "CSR"])
    alcalt_cur = dedupe_rows([r for r in alc_alt_rows if r["rarity_key"] == "CUR"])
    if alcalt_cur:
        alcalt_pools["CUR"] = alcalt_cur
    alc_base_slugs = {r["slug"] for r in alc_base_rows}
    alc_alter_exclusive_rows = [
        r for r in alc_alt_rows
        if r["rarity_key"] != "CSR" and r["slug"] not in alc_base_slugs
    ]
    alcalt_pools["ALTER_EXCLUSIVE"] = dedupe_rows(alc_alter_exclusive_rows)
    pools_by_collation[ALC_ALTER_COLLATION["id"]] = alcalt_pools

    ftc_rows = rows_for_prefixes(FTC_PREFIXES)
    pools_by_collation[FTC_COLLATION["id"]] = pools_from_rows(ftc_rows)

    doa_1e_rows = rows_for_prefixes(DOA_1E_PREFIXES)
    doa_alt_rows = rows_for_prefixes(DOA_ALTER_PREFIXES)

    doa_1e_pools = pools_from_rows(doa_1e_rows)
    pools_by_collation[DOA_1E_COLLATION["id"]] = doa_1e_pools

    doa_alt_pools = pools_from_rows(doa_alt_rows)
    pools_by_collation[DOA_ALTER_COLLATION["id"]] = doa_alt_pools

    mrc_base_rows = rows_by_set.get(MRC_BASE_SET, [])
    mrc_1e_rows = rows_by_set.get(MRC_FIRST_ED_SET, [])
    mrc_alt_rows = rows_by_set.get(MRC_ALTER_SET, [])

    mrc_base_pools = pools_from_rows(mrc_base_rows)

    mrc1e_pools = clone_pools(mrc_base_pools)
    mrc1e_pools["CSR"] = dedupe_rows([r for r in mrc_1e_rows if r["rarity_key"] == "CSR"])
    mrc1e_cur = dedupe_rows([r for r in mrc_1e_rows if r["rarity_key"] == "CUR"])
    if mrc1e_cur:
        mrc1e_pools["CUR"] = mrc1e_cur
    pools_by_collation[MRC_1E_COLLATION["id"]] = mrc1e_pools

    mrcalt_pools = clone_pools(mrc_base_pools)
    mrcalt_pools["CSR"] = dedupe_rows([r for r in mrc_alt_rows if r["rarity_key"] == "CSR"])
    mrcalt_cur = dedupe_rows([r for r in mrc_alt_rows if r["rarity_key"] == "CUR"])
    if mrcalt_cur:
        mrcalt_pools["CUR"] = mrcalt_cur
    base_slugs = {r["slug"] for r in mrc_base_rows}
    alter_exclusive_rows = [
        r for r in mrc_alt_rows
        if r["rarity_key"] != "CSR" and r["slug"] not in base_slugs
    ]
    mrcalt_pools["ALTER_EXCLUSIVE"] = dedupe_rows(alter_exclusive_rows)
    pools_by_collation[MRC_ALTER_COLLATION["id"]] = mrcalt_pools

    all_rows = []
    for set_rows in rows_by_set.values():
        all_rows.extend(set_rows)
    for cid in supplemental_rows_by_collation:
        all_rows.extend(supplemental_rows_by_collation[cid])
    all_rows = dedupe_rows(all_rows)

    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    lines = []
    lines.append("-- Auto-generated GA collation data")
    lines.append("-- Source: api.gatcg.com/cards/search")
    set_filter_parts = []
    if target_set_names:
        set_filter_parts.append(", ".join(target_set_names))
    if target_set_prefixes:
        set_filter_parts.append("prefixes: " + ", ".join(target_set_prefixes))
    lines.append("-- Set filter: " + " | ".join(set_filter_parts))
    lines.append(f"-- Generated: {generated_at}")
    lines.append("")
    lines.append("local M = {")
    lines.append("  meta = {")
    lines.append(f"    generated_at = {lua_quote(generated_at)},")
    lines.append(f"    source_api = {lua_quote(args.api)},")
    lines.append(f"    set_names = {lua_list_str(target_set_names)},")
    lines.append("  },")
    output_card_map_block(lines, all_rows)
    lines.append("  pools = {")

    requested_pool_defs = []

    for spec in STANDARD_COLLATIONS:
        cid = spec["id"]
        pools = pools_by_collation[cid]
        for pool_name in POOL_ORDER:
            requested_pool_defs.append((pool_key(cid, pool_name), pools.get(pool_name, [])))

    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(MRC_1E_COLLATION["id"], pool_name), pools_by_collation[MRC_1E_COLLATION["id"]].get(pool_name, [])))
    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(MRC_ALTER_COLLATION["id"], pool_name), pools_by_collation[MRC_ALTER_COLLATION["id"]].get(pool_name, [])))
    requested_pool_defs.append((pool_key(MRC_ALTER_COLLATION["id"], "ALTER_EXCLUSIVE"), pools_by_collation[MRC_ALTER_COLLATION["id"]].get("ALTER_EXCLUSIVE", [])))

    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(AMB_1E_COLLATION["id"], pool_name), pools_by_collation[AMB_1E_COLLATION["id"]].get(pool_name, [])))
    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(AMB_ALTER_COLLATION["id"], pool_name), pools_by_collation[AMB_ALTER_COLLATION["id"]].get(pool_name, [])))
    requested_pool_defs.append((pool_key(AMB_ALTER_COLLATION["id"], "ALTER_EXCLUSIVE"), pools_by_collation[AMB_ALTER_COLLATION["id"]].get("ALTER_EXCLUSIVE", [])))

    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(ALC_COLLATION["id"], pool_name), pools_by_collation[ALC_COLLATION["id"]].get(pool_name, [])))
    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(ALC_ALTER_COLLATION["id"], pool_name), pools_by_collation[ALC_ALTER_COLLATION["id"]].get(pool_name, [])))
    requested_pool_defs.append((pool_key(ALC_ALTER_COLLATION["id"], "ALTER_EXCLUSIVE"), pools_by_collation[ALC_ALTER_COLLATION["id"]].get("ALTER_EXCLUSIVE", [])))

    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(FTC_COLLATION["id"], pool_name), pools_by_collation[FTC_COLLATION["id"]].get(pool_name, [])))

    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(DOA_1E_COLLATION["id"], pool_name), pools_by_collation[DOA_1E_COLLATION["id"]].get(pool_name, [])))
    for pool_name in POOL_ORDER:
        requested_pool_defs.append((pool_key(DOA_ALTER_COLLATION["id"], pool_name), pools_by_collation[DOA_ALTER_COLLATION["id"]].get(pool_name, [])))

    canonical_for_sig = {}
    alias_map = {}
    canonical_defs = []
    for key_name, rows in requested_pool_defs:
        sig = tuple(r["uuid"] for r in sort_uuid_rows(rows or []))
        if sig in canonical_for_sig:
            alias_map[key_name] = canonical_for_sig[sig]
        else:
            canonical_for_sig[sig] = key_name
            canonical_defs.append((key_name, rows or []))

    for key_name, rows in canonical_defs:
        output_pool_block(lines, key_name, rows)

    lines.append("  },")
    lines.append('  collations = {')

    for spec in STANDARD_COLLATIONS:
        add_standard_collation_block(
            lines,
            spec["id"],
            spec["collation_name"],
            uncommon_slots=spec.get("uncommon_slots", 2),
            common_slots=spec.get("common_slots", 3),
        )

    add_standard_collation_block(lines, MRC_1E_COLLATION["id"], MRC_1E_COLLATION["collation_name"])
    add_alter_collation_block(lines, MRC_ALTER_COLLATION["id"], MRC_ALTER_COLLATION["collation_name"])
    add_standard_collation_block(lines, AMB_1E_COLLATION["id"], AMB_1E_COLLATION["collation_name"], uncommon_slots=3, common_slots=9)
    add_alter_collation_block(lines, AMB_ALTER_COLLATION["id"], AMB_ALTER_COLLATION["collation_name"], uncommon_slots=3, common_slots=5)
    add_standard_collation_block(lines, ALC_COLLATION["id"], ALC_COLLATION["collation_name"], uncommon_slots=3, common_slots=6)
    add_alter_collation_block(lines, ALC_ALTER_COLLATION["id"], ALC_ALTER_COLLATION["collation_name"], uncommon_slots=3, common_slots=5)
    add_standard_collation_block(lines, FTC_COLLATION["id"], FTC_COLLATION["collation_name"])
    add_standard_collation_block(lines, DOA_1E_COLLATION["id"], DOA_1E_COLLATION["collation_name"], uncommon_slots=3, common_slots=6)
    add_standard_collation_block(lines, DOA_ALTER_COLLATION["id"], DOA_ALTER_COLLATION["collation_name"], uncommon_slots=3, common_slots=6)

    lines.append("  },")
    lines.append("}")
    lines.append('M.collations["ABYSSAL_HEAVEN_8_CARD"] = M.collations["HVN_8_CARD"]')
    lines.append('M.collations["MRC1E_8_CARD"] = M.collations["MRC_1E_8_CARD"]')
    lines.append('M.collations["AMB1E_8_CARD"] = M.collations["AMB_1E_8_CARD"]')
    lines.append('M.collations["ALCALT_12_CARD"] = M.collations["ALC_ALTER_12_CARD"]')
    lines.append('M.collations["DOA1E_8_CARD"] = M.collations["DOA_1E_12_CARD"]')
    for alias_key in sorted(alias_map.keys()):
        target_key = alias_map[alias_key]
        if alias_key != target_key:
            lines.append(f'M.pools["{alias_key}"] = M.pools["{target_key}"]')
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
    lines.append("    uuid = card.uuid,")
    lines.append("    image = card.image,")
    lines.append("    orientation = card.orientation,")
    lines.append("    orientations = card.orientations,")
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
    for spec in STANDARD_COLLATIONS:
        pools = pools_by_collation[spec["id"]]
        print(f"Pool sizes for {spec['collation_name']}:")
        for pool_name in POOL_ORDER:
            print(f"  {pool_name}: {len(pools.get(pool_name, []))}")
    print(f"Pool sizes for {MRC_1E_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[MRC_1E_COLLATION['id']].get(pool_name, []))}")
    print(f"Pool sizes for {MRC_ALTER_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[MRC_ALTER_COLLATION['id']].get(pool_name, []))}")
    print(f"  ALTER_EXCLUSIVE: {len(pools_by_collation[MRC_ALTER_COLLATION['id']].get('ALTER_EXCLUSIVE', []))}")
    print(f"Pool sizes for {AMB_1E_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[AMB_1E_COLLATION['id']].get(pool_name, []))}")
    print(f"Pool sizes for {AMB_ALTER_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[AMB_ALTER_COLLATION['id']].get(pool_name, []))}")
    print(f"  ALTER_EXCLUSIVE: {len(pools_by_collation[AMB_ALTER_COLLATION['id']].get('ALTER_EXCLUSIVE', []))}")
    print(f"Pool sizes for {ALC_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[ALC_COLLATION['id']].get(pool_name, []))}")
    print(f"Pool sizes for {ALC_ALTER_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[ALC_ALTER_COLLATION['id']].get(pool_name, []))}")
    print(f"  ALTER_EXCLUSIVE: {len(pools_by_collation[ALC_ALTER_COLLATION['id']].get('ALTER_EXCLUSIVE', []))}")
    print(f"Pool sizes for {FTC_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[FTC_COLLATION['id']].get(pool_name, []))}")
    print(f"Pool sizes for {DOA_1E_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[DOA_1E_COLLATION['id']].get(pool_name, []))}")
    print(f"Pool sizes for {DOA_ALTER_COLLATION['collation_name']}:")
    for pool_name in POOL_ORDER:
        print(f"  {pool_name}: {len(pools_by_collation[DOA_ALTER_COLLATION['id']].get(pool_name, []))}")


if __name__ == "__main__":
    main()
