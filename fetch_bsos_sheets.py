#!/usr/bin/env python3
"""
Fetch BSOS (Share of Search) data directly from the two Brandstack Google
Sheets and write it into data/bsos_pan_monthly.csv, bsos_pan_weekly.csv,
bsos_pan_india_daily.csv and bsos_city_daily.csv.

Uses the same read-only Sheets OAuth token as fetch_sheets_gsc.py
(SHEETS_REFRESH_TOKEN — set up once via setup_sheets_auth.py).

Sources:
  All-India day/week/month  — sheet 1GleR3Nf_wpIx_GN7PD_hoB0XxtTNPZCz6yhdLQk8rbg
                               tabs: "Day", "Week", "Month"
  City-level daily          — sheet 1R9WbF_Avt4RMofh-KwHFBT33saIpIRcLy3HRl62EKEM
                               tab: "[Daily] City Deep Dive"

Every fetch is validated (expected columns present, dates parse, values in
0-100 range, row count not a suspicious drop vs the existing file) before
any CSV is overwritten. A failed validation leaves the existing CSV
untouched and raises, so a broken sheet edit can't silently corrupt the
live dashboard.

Run:
  python3 fetch_bsos_sheets.py
"""

import os
import sys
import csv
import requests
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path("data")

SHEET_ALL_INDIA = "1GleR3Nf_wpIx_GN7PD_hoB0XxtTNPZCz6yhdLQk8rbg"
SHEET_CITY       = "1R9WbF_Avt4RMofh-KwHFBT33saIpIRcLy3HRl62EKEM"
CITY_TAB         = "[Daily] City Deep Dive"

TOKEN_URL = "https://oauth2.googleapis.com/token"

# Sheet header text -> internal brand key
BRAND_MAP = {
    "cardekho": "Cardekho",
    "cars24":   "Cars24",
    "carwale":  "CarWale",
    "mahindra first choice": "MFC",
    "maruti true value":     "MTV",
    "olx auto": "OLX",
    "spinny":   "Spinny",
}
EXPECTED_BRANDS = set(BRAND_MAP.values())
MIN_ROW_RATIO = 0.7   # abort if new fetch has fewer than 70% of the previous file's rows


class ValidationError(Exception):
    pass


def load_env():
    # Local dev reads .env; in CI the secrets are already real env vars and no .env file exists.
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
    """Parse a sheet cell like '16.8%' -> 16.8 (float). Blank/None -> None."""
    if raw is None or str(raw).strip() == "":
        return None
    v = float(str(raw).replace("%", "").replace(",", "").strip())
    if not (-1 <= v <= 100):
        raise ValidationError(f"value out of expected 0-100%% range: {raw!r}")
    return v


def map_brand_columns(header_row):
    """Given a header row, return {csv_col_index: brand_key} for recognized brand columns."""
    mapping = {}
    for i, h in enumerate(header_row):
        key = BRAND_MAP.get(str(h).strip().lower())
        if key:
            mapping[i] = key
    missing = EXPECTED_BRANDS - set(mapping.values())
    if missing:
        raise ValidationError(f"missing expected brand columns: {sorted(missing)} (header was {header_row!r})")
    return mapping


def find_header_row(rows, first_col_name):
    """Locate the row whose first cell matches first_col_name (case-insensitive)."""
    for i, row in enumerate(rows):
        if row and str(row[0]).strip().lower() == first_col_name.lower():
            return i
    raise ValidationError(f"could not find header row starting with {first_col_name!r} in first {len(rows)} rows")


def existing_row_count(csv_path):
    if not csv_path.exists():
        return None
    with open(csv_path, newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus header


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


# ── All-India Day / Week / Month ────────────────────────────────────────────
def fetch_all_india_tab(token, tab, date_col_name):
    rows = fetch_values(token, SHEET_ALL_INDIA, f"{tab}!A1:Z1000")
    hdr_idx = find_header_row(rows, date_col_name)
    header = rows[hdr_idx]
    brand_cols = map_brand_columns(header)
    data_rows = rows[hdr_idx + 1:]

    parsed = []
    for r in data_rows:
        if not r or not r[0].strip():
            continue
        date_raw = r[0].strip()
        vals = {}
        for i, brand in brand_cols.items():
            vals[brand] = pct(r[i]) if i < len(r) else None
        parsed.append((date_raw, vals))
    if not parsed:
        raise ValidationError(f"{tab}: zero data rows parsed")
    return parsed


def build_daily(token):
    parsed = fetch_all_india_tab(token, "Day", "Date")
    rows = []
    for date_raw, vals in parsed:
        d = datetime.strptime(date_raw, "%b %d, %Y").date()
        rows.append({"date": d.isoformat(), **vals})
    rows.sort(key=lambda r: r["date"])
    path = DATA / "bsos_pan_india_daily.csv"
    check_row_count(len(rows), path, "BSOS all-India daily")
    write_csv(path, ["date"] + sorted(EXPECTED_BRANDS), rows)
    print(f"  ✓ bsos_pan_india_daily.csv: {len(rows)} days ({rows[0]['date']} → {rows[-1]['date']})")


def build_weekly(token):
    parsed = fetch_all_india_tab(token, "Week", "Week of")
    rows = []
    for date_raw, vals in parsed:
        ws = datetime.strptime(date_raw, "%b %d, %Y").date()
        we = ws + timedelta(days=6)
        label = f"{ws.strftime('%d %b')} – {we.strftime('%d %b %Y')}"
        rows.append({"week_start": ws.isoformat(), "week": label, **vals})
    rows.sort(key=lambda r: r["week_start"])
    path = DATA / "bsos_pan_weekly.csv"
    check_row_count(len(rows), path, "BSOS all-India weekly")
    write_csv(path, ["week_start", "week"] + sorted(EXPECTED_BRANDS), rows)
    print(f"  ✓ bsos_pan_weekly.csv: {len(rows)} weeks ({rows[0]['week_start']} → {rows[-1]['week_start']})")


def build_monthly(token):
    parsed = fetch_all_india_tab(token, "Month", "Month")
    rows = []
    for date_raw, vals in parsed:
        m = datetime.strptime(date_raw, "%b %Y").date()
        rows.append({"month": f"{m.year:04d}-{m.month:02d}", **vals})
    rows.sort(key=lambda r: r["month"])
    path = DATA / "bsos_pan_monthly.csv"
    check_row_count(len(rows), path, "BSOS all-India monthly")
    write_csv(path, ["month"] + sorted(EXPECTED_BRANDS), rows)
    print(f"  ✓ bsos_pan_monthly.csv: {len(rows)} months ({rows[0]['month']} → {rows[-1]['month']})")


# ── City-level daily ─────────────────────────────────────────────────────────
def build_city_daily(token):
    rows_raw = fetch_values(token, SHEET_CITY, f"{CITY_TAB}!A1:I8000")
    hdr_idx = find_header_row(rows_raw, "Brandstack City")
    header = rows_raw[hdr_idx]
    if len(header) < 2 or str(header[1]).strip().lower() != "date":
        raise ValidationError(f"City Deep Dive: expected column B to be 'date', got {header[1]!r}")
    brand_cols = map_brand_columns(header)  # indices are offset by the 2 leading (city,date) cols
    data_rows = rows_raw[hdr_idx + 1:]

    out = []
    for r in data_rows:
        if len(r) < 2 or not r[0].strip() or not r[1].strip():
            continue
        city = r[0].strip()
        d = datetime.strptime(r[1].strip(), "%b %d, %Y").date()
        vals = {}
        for i, brand in brand_cols.items():
            vals[brand] = pct(r[i]) if i < len(r) else None
        out.append({"city": city, "date": d.isoformat(), **vals})

    if not out:
        raise ValidationError("City Deep Dive: zero data rows parsed")
    cities = sorted(set(r["city"] for r in out))
    if len(cities) < 5:
        raise ValidationError(f"City Deep Dive: only {len(cities)} distinct cities found ({cities}) — expected many more")

    out.sort(key=lambda r: (r["city"], r["date"]))
    path = DATA / "bsos_city_daily.csv"
    check_row_count(len(out), path, "BSOS city daily")
    write_csv(path, ["city", "date"] + sorted(EXPECTED_BRANDS), out)
    print(f"  ✓ bsos_city_daily.csv: {len(out)} rows across {len(cities)} cities "
          f"({out[0]['date']} → {out[-1]['date']})")


def main():
    load_env()
    token = get_token()

    print("  Fetching BSOS all-India (Day / Week / Month tabs)…")
    for label, fn in [("daily", build_daily), ("weekly", build_weekly), ("monthly", build_monthly)]:
        try:
            fn(token)
        except (ValidationError, ValueError, KeyError) as e:
            print(f"  ✗ BSOS all-India {label} fetch failed validation, existing CSV left untouched: {e}")

    print("  Fetching BSOS city-level (City Deep Dive tab)…")
    try:
        build_city_daily(token)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"  ✗ BSOS city daily fetch failed validation, existing CSV left untouched: {e}")


if __name__ == "__main__":
    main()
