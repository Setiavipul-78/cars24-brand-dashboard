#!/usr/bin/env python3
"""
Fetch Google Search Console brand search impressions for India.
Uses OAuth refresh token (same credentials.json as YouTube).

Run setup once:
  python3 setup_gsc_auth.py

Then fetch:
  python3 fetch_gsc.py           # incremental (last 14 days)
  python3 fetch_gsc.py --full    # full history from Nov 2023
"""

import os
import sys
import csv
from datetime import date, timedelta
from pathlib import Path

DATA    = Path("data")
SITE    = "https://www.cars24.com/"
CSV_OUT = DATA / "gsc_daily_india.csv"

# Matches: cars24, car24, cars 24, car 24, cars-24
BRAND_REGEX = r"cars?\s?24|car24"

TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_access_token():
    """Exchange refresh token for a short-lived access token."""
    import requests
    client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GSC_REFRESH_TOKEN", "")

    if not refresh_token:
        print("  ! GSC_REFRESH_TOKEN not set. Run: python3 setup_gsc_auth.py")
        return None
    if not client_id or not client_secret:
        print("  ! GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set.")
        return None

    resp = requests.post(TOKEN_URL, data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token",
    })
    if resp.status_code != 200:
        print(f"  ! Token refresh failed: {resp.text}")
        return None
    return resp.json()["access_token"]


def query_gsc(access_token, start: date, end: date):
    """Query GSC searchAnalytics for brand impressions in India, grouped by date."""
    import requests
    from urllib.parse import quote
    url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(SITE, safe='')}/searchAnalytics/query"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    all_rows = []
    start_row = 0

    while True:
        body = {
            "startDate": str(start),
            "endDate":   str(end),
            "dimensions": ["date"],
            "dimensionFilterGroups": [{
                "filters": [
                    {
                        "dimension": "country",
                        "operator":  "equals",
                        "expression": "ind"
                    },
                    {
                        "dimension": "query",
                        "operator":  "includingRegex",
                        "expression": BRAND_REGEX
                    }
                ]
            }],
            "rowLimit":  25000,
            "startRow":  start_row,
            "dataState": "all"   # includes most-recent 2 days (may revise later)
        }

        resp = requests.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            print(f"  ! GSC API error {resp.status_code}: {resp.text}")
            return None

        rows = resp.json().get("rows", [])
        if not rows:
            break

        for row in rows:
            all_rows.append({
                "date":        row["keys"][0],
                "impressions": int(row.get("impressions", 0)),
                "clicks":      int(row.get("clicks", 0)),
            })

        if len(rows) < 25000:
            break
        start_row += 25000

    return all_rows


def load_existing():
    if not CSV_OUT.exists():
        return {}
    with open(CSV_OUT, newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def main():
    full_refresh = "--full" in sys.argv
    DATA.mkdir(exist_ok=True)

    # Load .env if running locally
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    access_token = get_access_token()
    if not access_token:
        print("  Keeping existing gsc_daily_india.csv unchanged.")
        return

    existing = load_existing()

    # Determine date range
    end_date = date.today() - timedelta(days=1)  # yesterday (dataState=all)
    if full_refresh or not existing:
        start_date = date(2023, 11, 1)
        print(f"  GSC: full fetch {start_date} → {end_date}")
    else:
        last = max(existing.keys())
        # Re-fetch last 14 days to catch any GSC revisions
        start_date = max(
            date.fromisoformat(last) - timedelta(days=14),
            date(2023, 11, 1)
        )
        print(f"  GSC: incremental {start_date} → {end_date}  (last on file: {last})")

    if start_date > end_date:
        print("  GSC: already up to date.")
        return

    rows = query_gsc(access_token, start_date, end_date)
    if rows is None:
        print("  ! GSC fetch failed — keeping existing CSV.")
        return

    print(f"  GSC API: {len(rows)} rows returned")

    if not rows:
        print("  ! No data returned — check that vipul.setia@cars24.com has GSC access")
        return

    # Merge with existing and write
    for row in rows:
        existing[row["date"]] = row

    sorted_rows = sorted(existing.values(), key=lambda r: r["date"])
    with open(CSV_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "impressions", "clicks"])
        writer.writeheader()
        writer.writerows(sorted_rows)

    print(f"  ✓ gsc_daily_india.csv: {len(sorted_rows)} days "
          f"({sorted_rows[0]['date']} → {sorted_rows[-1]['date']})")


if __name__ == "__main__":
    main()
