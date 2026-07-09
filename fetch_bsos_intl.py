#!/usr/bin/env python3
"""
Fetch BSOS (Share of Search) data for UAE and Australia from their own
dedicated Brandstack Google Sheets (separate from India's, which
fetch_bsos_sheets.py handles — different sheet IDs, different competitor
sets, different tab layouts).

Uses the same read-only Sheets OAuth token as fetch_bsos_sheets.py
(SHEETS_REFRESH_TOKEN — set up once via setup_sheets_auth.py).

Sources:
  UAE  — sheet 1XrDtorf_obSYex1NSuSXcoawbfneuTi1JxVLxlmA8rw
         tabs: "BSOS Trend - Monthly", "BSOS Trend - Weekly", "BSOS Trend - Daily"
         single column-block (no per-city breakdown)
  AUS  — sheet 1oXgpR60cC22qQOzjMS1-n-LCXMXDC1TzE8JH8OCeDvA
         tabs: "BSOS - Monthly", "BSOS - Weekly" (no Daily tab)
         4 side-by-side column blocks: AUS (national), NSW, QLD, VIC

Every fetch is validated (expected brand columns present, dates parse,
values in 0-100 range, row count not a suspicious drop vs the existing
file) before any CSV is overwritten — same safety approach as
fetch_bsos_sheets.py, so a broken sheet edit can't silently corrupt the
live dashboard.

Writes:
  bsos_uae_monthly.csv, bsos_uae_weekly.csv, bsos_uae_daily.csv
  bsos_aus_monthly.csv, bsos_aus_weekly.csv          — national (AUS block)
  bsos_aus_region_monthly.csv, bsos_aus_region_weekly.csv — region,date,brand... (NSW/QLD/VIC)

Run:
  python3 fetch_bsos_intl.py
"""

import os
import csv
import requests
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path("data")

SHEET_UAE = "1XrDtorf_obSYex1NSuSXcoawbfneuTi1JxVLxlmA8rw"
SHEET_AUS = "1oXgpR60cC22qQOzjMS1-n-LCXMXDC1TzE8JH8OCeDvA"

TOKEN_URL = "https://oauth2.googleapis.com/token"

BRAND_MAP_UAE = {
    "alba cars":  "AlbaCars",
    "automall":   "Automall",
    "cars24":     "Cars24",
    "dubizzle":   "Dubizzle",
    "kavak":      "Kavak",
    "rma motors": "RMAMotors",
}
BRAND_MAP_AUS = {
    "autotrader":  "Autotrader",
    "carma":       "Carma",
    "cars24":      "Cars24",
    "carsales":    "Carsales",
    "easyauto123": "Easyauto123",
}
MIN_ROW_RATIO = 0.7


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


def fetch_values(token, sheet_id, rng):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{requests.utils.quote(rng)}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json().get("values", [])


def pct(raw):
    if raw is None or str(raw).strip() == "":
        return None
    v = float(str(raw).replace("%", "").replace(",", "").strip())
    if not (-1 <= v <= 100):
        raise ValidationError(f"value out of expected 0-100%% range: {raw!r}")
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


def find_header_row(rows, first_col_name):
    for i, row in enumerate(rows):
        if row and str(row[0]).strip().lower() == first_col_name.lower():
            return i
    raise ValidationError(f"could not find header row starting with {first_col_name!r} in first {len(rows)} rows")


def parse_date_cell(raw, fmt_candidates):
    for fmt in fmt_candidates:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValidationError(f"could not parse date {raw!r} with any of {fmt_candidates}")


# ── UAE: single column-block per tab ────────────────────────────────────────
def fetch_uae_tab(token, tab, date_col_name):
    rows = fetch_values(token, SHEET_UAE, f"'{tab}'!A1:Z2000")
    hdr_idx = find_header_row(rows, date_col_name)
    header = rows[hdr_idx]
    brand_cols = {}
    for i, h in enumerate(header):
        key = BRAND_MAP_UAE.get(str(h).strip().lower())
        if key:
            brand_cols[i] = key
    missing = set(BRAND_MAP_UAE.values()) - set(brand_cols.values())
    if missing:
        raise ValidationError(f"{tab}: missing expected brand columns: {sorted(missing)} (header was {header!r})")

    parsed = []
    for r in rows[hdr_idx + 1:]:
        if not r or not r[0].strip():
            continue
        vals = {brand: (pct(r[i]) if i < len(r) else None) for i, brand in brand_cols.items()}
        parsed.append((r[0].strip(), vals))
    if not parsed:
        raise ValidationError(f"{tab}: zero data rows parsed")
    return parsed


def build_uae_daily(token):
    parsed = fetch_uae_tab(token, "BSOS Trend - Daily", "Date")
    rows = [{"date": parse_date_cell(d, ["%b %d, %Y"]).isoformat(), **v} for d, v in parsed]
    rows.sort(key=lambda r: r["date"])
    path = DATA / "bsos_uae_daily.csv"
    check_row_count(len(rows), path, "BSOS UAE daily")
    write_csv(path, ["date"] + sorted(BRAND_MAP_UAE.values()), rows)
    print(f"  ✓ bsos_uae_daily.csv: {len(rows)} days ({rows[0]['date']} → {rows[-1]['date']})")


def build_uae_weekly(token):
    parsed = fetch_uae_tab(token, "BSOS Trend - Weekly", "Week of")
    rows = []
    for d, v in parsed:
        ws = parse_date_cell(d, ["%b %d, %Y"])
        we = ws + timedelta(days=6)
        rows.append({"week_start": ws.isoformat(), "week": f"{ws.strftime('%d %b')} – {we.strftime('%d %b %Y')}", **v})
    rows.sort(key=lambda r: r["week_start"])
    path = DATA / "bsos_uae_weekly.csv"
    check_row_count(len(rows), path, "BSOS UAE weekly")
    write_csv(path, ["week_start", "week"] + sorted(BRAND_MAP_UAE.values()), rows)
    print(f"  ✓ bsos_uae_weekly.csv: {len(rows)} weeks ({rows[0]['week_start']} → {rows[-1]['week_start']})")


def build_uae_monthly(token):
    parsed = fetch_uae_tab(token, "BSOS Trend - Monthly", "Month")
    rows = []
    for d, v in parsed:
        m = parse_date_cell(d, ["%b %Y"])
        rows.append({"month": f"{m.year:04d}-{m.month:02d}", **v})
    rows.sort(key=lambda r: r["month"])
    path = DATA / "bsos_uae_monthly.csv"
    check_row_count(len(rows), path, "BSOS UAE monthly")
    write_csv(path, ["month"] + sorted(BRAND_MAP_UAE.values()), rows)
    print(f"  ✓ bsos_uae_monthly.csv: {len(rows)} months ({rows[0]['month']} → {rows[-1]['month']})")


# ── AUS: 4 side-by-side region blocks (AUS/NSW/QLD/VIC) per tab ────────────
def parse_region_blocks(rows, date_col_name):
    """Row 0 = region names (one per block start), row 1 = header
    (Month/Week + brand cols) repeated per block, blank column separates
    blocks. Returns {region: [(date_str, {brand: pct}), ...]}."""
    if len(rows) < 3:
        raise ValidationError("expected at least 3 rows (region row, header row, data)")
    region_row, header_row = rows[0], rows[1]
    block_starts = [i for i, v in enumerate(region_row) if str(v).strip()]
    if not block_starts:
        raise ValidationError(f"no region names found in row 0: {region_row!r}")

    blocks = {}
    for bi, start in enumerate(block_starts):
        region = str(region_row[start]).strip()
        end = block_starts[bi + 1] if bi + 1 < len(block_starts) else len(header_row)
        if start >= len(header_row) or str(header_row[start]).strip().lower() != date_col_name.lower():
            raise ValidationError(f"region {region!r}: expected {date_col_name!r} at column {start}, "
                                   f"got {header_row[start] if start < len(header_row) else None!r}")
        brand_cols = {}
        for i in range(start, end):
            if i >= len(header_row):
                break
            key = BRAND_MAP_AUS.get(str(header_row[i]).strip().lower())
            if key:
                brand_cols[i] = key
        missing = set(BRAND_MAP_AUS.values()) - set(brand_cols.values())
        if missing:
            raise ValidationError(f"region {region!r}: missing expected brand columns: {sorted(missing)}")

        data = []
        for r in rows[2:]:
            if len(r) <= start or not str(r[start]).strip():
                continue
            vals = {brand: (pct(r[i]) if i < len(r) else None) for i, brand in brand_cols.items()}
            data.append((str(r[start]).strip(), vals))
        if not data:
            raise ValidationError(f"region {region!r}: zero data rows parsed")
        blocks[region] = data
    return blocks


def build_aus_monthly(token):
    rows = fetch_values(token, SHEET_AUS, "'BSOS - Monthly'!A1:AB2000")
    blocks = parse_region_blocks(rows, "Month")

    national = blocks.pop("AUS", None)
    if national is None:
        raise ValidationError("AUS - Monthly: no 'AUS' national block found")
    nat_rows = []
    for d, v in national:
        m = parse_date_cell(d, ["%b %Y"])
        nat_rows.append({"month": f"{m.year:04d}-{m.month:02d}", **v})
    nat_rows.sort(key=lambda r: r["month"])
    path = DATA / "bsos_aus_monthly.csv"
    check_row_count(len(nat_rows), path, "BSOS AUS national monthly")
    write_csv(path, ["month"] + sorted(BRAND_MAP_AUS.values()), nat_rows)
    print(f"  ✓ bsos_aus_monthly.csv: {len(nat_rows)} months ({nat_rows[0]['month']} → {nat_rows[-1]['month']})")

    region_rows = []
    for region, data in blocks.items():
        for d, v in data:
            m = parse_date_cell(d, ["%b %Y"])
            region_rows.append({"region": region, "month": f"{m.year:04d}-{m.month:02d}", **v})
    region_rows.sort(key=lambda r: (r["region"], r["month"]))
    path = DATA / "bsos_aus_region_monthly.csv"
    check_row_count(len(region_rows), path, "BSOS AUS region monthly")
    write_csv(path, ["region", "month"] + sorted(BRAND_MAP_AUS.values()), region_rows)
    print(f"  ✓ bsos_aus_region_monthly.csv: {len(region_rows)} rows across {len(blocks)} regions ({sorted(blocks.keys())})")


def build_aus_weekly(token):
    rows = fetch_values(token, SHEET_AUS, "'BSOS - Weekly'!A1:AB2000")
    blocks = parse_region_blocks(rows, "Week")

    national = blocks.pop("AUS", None)
    if national is None:
        raise ValidationError("AUS - Weekly: no 'AUS' national block found")
    nat_rows = []
    for d, v in national:
        ws = parse_date_cell(d, ["%b %d, %Y"])
        we = ws + timedelta(days=6)
        nat_rows.append({"week_start": ws.isoformat(), "week": f"{ws.strftime('%d %b')} – {we.strftime('%d %b %Y')}", **v})
    nat_rows.sort(key=lambda r: r["week_start"])
    path = DATA / "bsos_aus_weekly.csv"
    check_row_count(len(nat_rows), path, "BSOS AUS national weekly")
    write_csv(path, ["week_start", "week"] + sorted(BRAND_MAP_AUS.values()), nat_rows)
    print(f"  ✓ bsos_aus_weekly.csv: {len(nat_rows)} weeks ({nat_rows[0]['week_start']} → {nat_rows[-1]['week_start']})")

    region_rows = []
    for region, data in blocks.items():
        for d, v in data:
            ws = parse_date_cell(d, ["%b %d, %Y"])
            region_rows.append({"region": region, "week_start": ws.isoformat(), **v})
    region_rows.sort(key=lambda r: (r["region"], r["week_start"]))
    path = DATA / "bsos_aus_region_weekly.csv"
    check_row_count(len(region_rows), path, "BSOS AUS region weekly")
    write_csv(path, ["region", "week_start"] + sorted(BRAND_MAP_AUS.values()), region_rows)
    print(f"  ✓ bsos_aus_region_weekly.csv: {len(region_rows)} rows across {len(blocks)} regions ({sorted(blocks.keys())})")


def main():
    load_env()
    token = get_token()

    print("  Fetching BSOS UAE (Monthly / Weekly / Daily tabs)…")
    for label, fn in [("monthly", build_uae_monthly), ("weekly", build_uae_weekly), ("daily", build_uae_daily)]:
        try:
            fn(token)
        except (ValidationError, ValueError, KeyError) as e:
            print(f"  ✗ BSOS UAE {label} fetch failed validation, existing CSV left untouched: {e}")

    print("  Fetching BSOS AUS (Monthly / Weekly tabs, national + region blocks)…")
    for label, fn in [("monthly", build_aus_monthly), ("weekly", build_aus_weekly)]:
        try:
            fn(token)
        except (ValidationError, ValueError, KeyError) as e:
            print(f"  ✗ BSOS AUS {label} fetch failed validation, existing CSV left untouched: {e}")


if __name__ == "__main__":
    main()
