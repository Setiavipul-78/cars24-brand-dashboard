#!/usr/bin/env python3
"""
Fetch Google Search Index data (Google Trends-style 0-100 relative index,
NOT a percentage share) directly from the Google Index sheet's three
relevant tabs, and write it into data/gindex_pan_monthly.csv,
gindex_city_brand_monthly.csv and gindex_city_generic_monthly.csv.

Uses the same read-only Sheets OAuth token as fetch_bsos_sheets.py
(SHEETS_REFRESH_TOKEN — set up once via setup_sheets_auth.py).

Sheet: 1d3umTUBQ1vKWzbhfdVr88kr8Stpn832V1mCSkfjQ51A
  "India"                — pan-India, two side-by-side blocks:
                            Cars24 branded (Month/Index/Rounded) and
                            Category/Generic (Month/Index/Rounded)
  "India-City (Brand)"   — city-level brand index, Month + 17 city columns
  "India-City (Generic)" — city-level category/generic index, same shape

IMPORTANT data-quality note: every tab reports "Index" (the relative
0-100ish number we want) alongside a "Rounded" column/block (an absolute
search-volume-looking count in the tens/hundreds of thousands) that must
be ignored per an explicit instruction — Index is "the right way to look
at it". The two city tabs additionally stack a second full copy of the
data (the Rounded block) below the Index block, separated by blank rows,
rather than side-by-side — so parsing must stop at the first blank row
after the header and never read past it.

Run:
  python3 fetch_gindex_sheets.py
"""

import os
import csv
import requests
from datetime import datetime
from pathlib import Path

DATA = Path("data")
SHEET = "1d3umTUBQ1vKWzbhfdVr88kr8Stpn832V1mCSkfjQ51A"
TOKEN_URL = "https://oauth2.googleapis.com/token"

MIN_ROW_RATIO = 0.7   # abort if new fetch has fewer than 70% of the previous file's rows
MAX_INDEX = 1000       # sanity ceiling — a leaked "Rounded" value would be tens of thousands, far above this


class ValidationError(Exception):
    pass


def load_env():
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_token():
    resp = requests.post(TOKEN_URL, data={
        "client_id":     os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["SHEETS_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_values(token, rng):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/{requests.utils.quote(rng)}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json().get("values", [])


def parse_month(raw):
    return datetime.strptime(raw.strip(), "%b %Y").date()


def parse_index(raw):
    if raw is None or str(raw).strip() == "":
        return None
    v = float(str(raw).replace(",", "").strip())
    if not (0 <= v <= MAX_INDEX):
        raise ValidationError(f"index value out of expected 0-{MAX_INDEX} range: {raw!r} — looks like a leaked 'Rounded' value")
    return v


def existing_row_count(csv_path):
    if not csv_path.exists():
        return None
    with open(csv_path, newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def check_row_count(new_count, csv_path, label):
    old = existing_row_count(csv_path)
    if old is not None and old > 0 and new_count < old * MIN_ROW_RATIO:
        raise ValidationError(
            f"{label}: new fetch has {new_count} rows vs {old} existing — "
            f"looks like a broken/partial fetch, aborting without overwriting {csv_path}"
        )


def write_csv(path, fieldnames, rows):
    DATA.mkdir(exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# ── Pan-India: Cars24 branded vs Category (Generic), Index only ────────────
def build_pan_india(token):
    rows = fetch_values(token, "India!A1:G1000")
    hdr_idx = next((i for i, r in enumerate(rows) if len(r) >= 2 and r[0].strip() == "Month" and r[1].strip() == "Index"), None)
    if hdr_idx is None:
        raise ValidationError("India tab: could not find 'Month | Index' header row")

    out = []
    for r in rows[hdr_idx + 1:]:
        if not r or not r[0].strip():
            break  # stop at first blank row — do not read into any trailing block
        brand_month = parse_month(r[0])
        brand_idx = parse_index(r[1]) if len(r) > 1 else None
        cat_month_raw = r[4].strip() if len(r) > 4 else ""
        if not cat_month_raw:
            raise ValidationError(f"India tab row for {r[0]}: category block month is blank — blocks out of alignment")
        cat_month = parse_month(cat_month_raw)
        if cat_month != brand_month:
            raise ValidationError(f"India tab: brand month {brand_month} != category month {cat_month} — blocks out of alignment")
        cat_idx = parse_index(r[5]) if len(r) > 5 else None
        out.append({"month": f"{brand_month.year:04d}-{brand_month.month:02d}", "Cars24": brand_idx, "Category": cat_idx})

    if not out:
        raise ValidationError("India tab: zero data rows parsed")
    out.sort(key=lambda r: r["month"])
    path = DATA / "gindex_pan_monthly.csv"
    check_row_count(len(out), path, "Google Index pan-India")
    write_csv(path, ["month", "Cars24", "Category"], out)
    print(f"  ✓ gindex_pan_monthly.csv: {len(out)} months ({out[0]['month']} → {out[-1]['month']})")


# ── City-level: Brand or Generic index, Month + 17 city columns ────────────
def build_city_tab(token, tab, out_name):
    rows = fetch_values(token, f"{tab}!A1:R1000")
    hdr_idx = next((i for i, r in enumerate(rows) if r and r[0].strip() == "Month" and len(r) > 1 and r[1].strip() != "Index"), None)
    if hdr_idx is None:
        raise ValidationError(f"{tab}: could not find city header row")
    cities = [c.strip() for c in rows[hdr_idx][1:] if c.strip()]
    if len(cities) < 5:
        raise ValidationError(f"{tab}: only {len(cities)} city columns found in header — expected many more")

    out = []
    for r in rows[hdr_idx + 1:]:
        if not r or not r[0].strip():
            break  # stop at first blank row — the sheet stacks a 'Rounded' block right after this gap
        m = parse_month(r[0])
        row = {"month": f"{m.year:04d}-{m.month:02d}"}
        for i, city in enumerate(cities):
            row[city] = parse_index(r[i + 1]) if i + 1 < len(r) else None
        out.append(row)

    if not out:
        raise ValidationError(f"{tab}: zero data rows parsed")
    out.sort(key=lambda r: r["month"])
    path = DATA / out_name
    check_row_count(len(out), path, f"Google Index {tab}")
    write_csv(path, ["month"] + cities, out)
    print(f"  ✓ {out_name}: {len(out)} months × {len(cities)} cities ({out[0]['month']} → {out[-1]['month']})")


def main():
    load_env()
    token = get_token()

    print("  Fetching Google Index (pan-India brand vs category)…")
    try:
        build_pan_india(token)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"  ✗ Google Index pan-India fetch failed validation, existing CSV left untouched: {e}")

    print("  Fetching Google Index (city-level brand)…")
    try:
        build_city_tab(token, "India-City (Brand)", "gindex_city_brand_monthly.csv")
    except (ValidationError, ValueError, KeyError) as e:
        print(f"  ✗ Google Index city brand fetch failed validation, existing CSV left untouched: {e}")

    print("  Fetching Google Index (city-level generic/category)…")
    try:
        build_city_tab(token, "India-City (Generic)", "gindex_city_generic_monthly.csv")
    except (ValidationError, ValueError, KeyError) as e:
        print(f"  ✗ Google Index city generic fetch failed validation, existing CSV left untouched: {e}")


if __name__ == "__main__":
    main()
