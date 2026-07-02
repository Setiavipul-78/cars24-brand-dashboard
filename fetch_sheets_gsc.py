#!/usr/bin/env python3
"""
Backfill gsc_daily_india.csv with historical daily data from the Google Sheet
"Google GSC Data" tab (Nov 2023 – Feb 2025).

Sheet:  1nnyBEchsIIoSVJ9WAOuXJwFRrmWR7DWzwweFH7bOwMc  gid=448835531
Tab:    Google GSC Data
Format: rows sorted newest→oldest, date in DD/MM/YYYY col A, impressions col C, clicks col B

Logic:
  - Parse all daily rows from the sheet
  - Keep only dates where the GSC API CSV (gsc_daily_india.csv) has no data
    i.e. dates < API_CUTOFF (2025-02-18)
  - Merge old sheet rows + newer API rows → write sorted CSV

Run:
  python3 fetch_sheets_gsc.py
"""

import os, csv, requests
from datetime import date, datetime
from pathlib import Path

SHEET_ID  = "1nnyBEchsIIoSVJ9WAOuXJwFRrmWR7DWzwweFH7bOwMc"
TAB_NAME  = "Google GSC Data"
DATA      = Path("data")
CSV_OUT   = DATA / "gsc_daily_india.csv"
API_CUTOFF = date(2025, 2, 18)   # GSC API data starts here; sheet fills before this

TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_token():
    for line in Path(".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    resp = requests.post(TOKEN_URL, data={
        "client_id":     os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["SHEETS_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    })
    return resp.json()["access_token"]


def fetch_sheet_daily(token):
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
           f"/values/{requests.utils.quote(TAB_NAME)}")
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    vals = r.json().get("values", [])

    rows = []
    for row in vals:
        if len(row) < 3:
            continue
        date_str = row[0].strip()
        if not date_str or not date_str[0].isdigit():
            continue
        try:
            # Sheet format: DD/MM/YYYY
            d = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            continue
        try:
            impressions = int(row[2].replace(",", ""))
            clicks      = int(row[1].replace(",", ""))
        except (ValueError, IndexError):
            continue
        rows.append({"date": d.isoformat(), "impressions": impressions, "clicks": clicks})

    return rows


def load_existing_csv():
    if not CSV_OUT.exists():
        return {}
    with open(CSV_OUT, newline="") as f:
        return {r["date"]: {"date": r["date"],
                            "impressions": int(float(r["impressions"])),
                            "clicks":      int(float(r["clicks"]))}
                for r in csv.DictReader(f)}


def main():
    DATA.mkdir(exist_ok=True)
    print("  Fetching Sheets token…")
    token = get_token()

    print("  Reading 'Google GSC Data' tab…")
    sheet_rows = fetch_sheet_daily(token)
    print(f"  Sheet: {len(sheet_rows)} daily rows parsed")

    # Only keep sheet rows for dates before API cutoff
    historical = {r["date"]: r for r in sheet_rows
                  if date.fromisoformat(r["date"]) < API_CUTOFF}
    print(f"  Historical rows (before {API_CUTOFF}): {len(historical)}")

    # Load existing API CSV (Feb 2025 onwards)
    existing = load_existing_csv()
    print(f"  Existing API CSV rows: {len(existing)}")

    # Merge: historical fills the past, API data wins for its range
    combined = {**historical, **existing}

    sorted_rows = sorted(combined.values(), key=lambda r: r["date"])
    with open(CSV_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "impressions", "clicks"])
        writer.writeheader()
        writer.writerows(sorted_rows)

    print(f"  ✓ gsc_daily_india.csv: {len(sorted_rows)} days "
          f"({sorted_rows[0]['date']} → {sorted_rows[-1]['date']})")


if __name__ == "__main__":
    main()
