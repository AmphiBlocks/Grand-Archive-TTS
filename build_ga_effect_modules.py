import csv, json, os, re, sys
from collections import defaultdict
from pathlib import Path

# ---------- config ----------
IN_PATH = sys.argv[1] if len(sys.argv) > 1 else "cards.csv"  # or .json
OUT_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "out_lua")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- helpers ----------
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

def pick_bucket(slug: str) -> str:
    return slug[:1].lower() if slug and slug[0].isalpha() else "_other"

def lua_long_bracket(s: str) -> str:
    """
    Safely wrap arbitrary text in Lua long brackets, choosing a level that
    does not appear in the string (e.g., [=[ ... ]=], [==[ ... ]==], ...).
    """
    s = "" if s is None else str(s)
    for eqs in range(0, 6):  # usually 0 or 1 is enough
        left  = "[" + ("=" * eqs) + "["
        right = "]" + ("=" * eqs) + "]"
        if (left not in s) and (right not in s):
            return f"{left}{s}{right}"
    # fallback: escape ‘]’ minimally (extremely unlikely path)
    s = s.replace("]", "]]")
    return f"[{s}]"

def row_iter(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as f:
            rdr = csv.DictReader(f)
            for r in rdr:
                yield {
                    "title": (r.get("title") or r.get("name") or "").strip(),
                    "effect_raw": (r.get("effect_raw") or r.get("effect") or "").strip(),
                    "side": (r.get("side") or "").strip().lower() or None,
                }
    elif path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        for it in data:
            yield {
                "title": (it.get("title") or it.get("name") or "").strip(),
                "effect_raw": (it.get("effect_raw") or it.get("effect") or "").strip(),
                "side": (it.get("side") or "").strip().lower() or None,
            }
    else:
        raise SystemExit("Input must be .csv or .json")

# ---------- build buckets ----------
buckets = defaultdict(dict)  # bucket -> { slug: effect_raw }

for row in row_iter(Path(IN_PATH)):
    title = row["title"]
    eff   = row["effect_raw"]
    side  = row["side"]
    if not title:
        continue
    slug = reduced_slug_from_title(title, side)
    if not slug:
        continue
    bucket = pick_bucket(slug)
    # last-write-wins if duplicates; adjust if you prefer to warn instead
    buckets[bucket][slug] = eff

# ---------- write Lua modules ----------
TEMPLATE = """-- Auto-generated GA effect table: {bucket}
-- Keys are reduced title slugs (and /front or /back for double-sided)
local M = {{
{entries}
}}

function getMap() return M end
"""

for bucket, kv in buckets.items():
    # stable order
    items = sorted(kv.items(), key=lambda x: x[0])
    lines = []
    for k, v in items:
        lines.append(f'  ["{k}"] = {lua_long_bracket(v)},')
    body = "\n".join(lines)
    out_name = f"GA_DATA_{bucket.upper()}.lua"
    (OUT_DIR / out_name).write_text(TEMPLATE.format(bucket=bucket, entries=body), encoding="utf-8")

print(f"Done. Wrote {len(buckets)} modules to: {OUT_DIR.resolve()}")
