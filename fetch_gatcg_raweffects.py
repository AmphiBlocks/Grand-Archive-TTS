# save as fetch_gatcg_effects.py
import csv, time, requests

API = "https://api.gatcg.com/cards/search"
OUT_CSV = "gatcg_effects.csv"
SLEEP = 0.1         # polite delay per page
RETRIES = 3
TIMEOUT = 20

def get_page(page: int):
    for attempt in range(1, RETRIES+1):
        try:
            r = requests.get(API, params={"page": page}, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"[warn] page {page} -> HTTP {r.status_code} (attempt {attempt})")
        except requests.RequestException as e:
            print(f"[warn] page {page} -> {e} (attempt {attempt})")
        time.sleep(0.5 * attempt)
    raise RuntimeError(f"Failed to fetch page {page} after {RETRIES} attempts")

def extract_records(card: dict):
    """Yield dicts: {slug, name, side, effect_raw} for the front + any backs."""
    out = []

    # Front / default
    front_slug = card.get("slug")
    front_name = card.get("name")
    front_text = card.get("effect_raw")
    out.append({
        "slug": front_slug or "",
        "name": front_name or "",
        "side": "front",
        "effect_raw": (front_text or "").strip()
    })

    # Collect 'other_orientations' from any edition/result_editions, dedup by slug
    seen = set()
    def add_orients(seq):
        if not isinstance(seq, list):
            return
        for o in seq:
            slug = (o or {}).get("slug")
            if not slug or slug in seen:
                continue
            seen.add(slug)
            name = o.get("name", "")
            # effect text can appear on the orientation object or inside its edition object
            text = o.get("effect_raw")
            if not text:
                text = (o.get("edition") or {}).get("effect_raw")
            out.append({
                "slug": slug,
                "name": name,
                "side": "back",
                "effect_raw": (text or "").strip()
            })

    # Try both locations where orientations commonly appear
    for ed in (card.get("editions") or []):
        add_orients(ed.get("other_orientations"))
    for ed in (card.get("result_editions") or []):
        add_orients(ed.get("other_orientations"))

    return out

def main():
    # discover total_pages on page 1
    first = get_page(1)
    total_pages = int(first.get("total_pages") or 1)
    print(f"Total pages reported: {total_pages}")

    rows = []
    # page 1 data already fetched
    for c in (first.get("data") or []):
        rows.extend(extract_records(c))

    for page in range(2, total_pages + 1):
        time.sleep(SLEEP)
        j = get_page(page)
        for c in (j.get("data") or []):
            rows.extend(extract_records(c))
        print(f"Fetched page {page}/{total_pages} (rows so far: {len(rows)})")

    # write CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["slug","name","side","effect_raw"])
        w.writeheader()
        w.writerows(rows)

    print(f"Done. Wrote {len(rows)} rows to {OUT_CSV}")

if __name__ == "__main__":
    main()