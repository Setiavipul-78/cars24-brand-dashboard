#!/usr/bin/env python3
"""
Fetch Google Search Console brand search impressions for India, Australia
and UAE. Uses OAuth refresh token (same credentials.json as YouTube) — the
same GSC_REFRESH_TOKEN already has access to the AU/UAE domain properties
(sc-domain:cars24.com.au, sc-domain:cars24.ae), confirmed via sites.list.

Run setup once:
  python3 setup_gsc_auth.py

Then fetch:
  python3 fetch_gsc.py           # incremental (last 14 days), all countries
  python3 fetch_gsc.py --full    # full history, all countries
"""

import os
import sys
import csv
from datetime import date, timedelta
from pathlib import Path

DATA = Path("data")

BRAND_REGEX = r"car 24|cars24|cars 24|24 car|cara 24|carz 24|card24|car24|24 cars"

# India is a URL-prefix property serving multiple countries, so it needs the
# "country" filter to isolate India traffic. AU/UAE are their own ccTLD
# domain properties (sc-domain:), so the whole property is already
# country-scoped — no country filter needed there. Each has its own daily
# CSV and its own full-history start date (only India has GSC access since
# Nov 2023; AU/UAE access was only granted more recently).
COUNTRIES = {
    "india": {"site": "https://www.cars24.com/", "country": "ind", "csv": "gsc_daily_india.csv",
              "full_start": date(2023, 11, 1)},
    "au":    {"site": "sc-domain:cars24.com.au",  "country": None,  "csv": "gsc_daily_au.csv",
              "full_start": date(2025, 1, 1)},
    "uae":   {"site": "sc-domain:cars24.ae",      "country": None,  "csv": "gsc_daily_uae.csv",
              "full_start": date(2025, 1, 1)},
}

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


def query_gsc(access_token, site: str, country, start: date, end: date):
    """Query GSC searchAnalytics for brand impressions on `site`, grouped by date."""
    import requests
    from urllib.parse import quote
    url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(site, safe='')}/searchAnalytics/query"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    all_rows = []
    start_row = 0

    filters = [{"dimension": "query", "operator": "includingRegex", "expression": BRAND_REGEX}]
    if country:
        filters.insert(0, {"dimension": "country", "operator": "equals", "expression": country})

    while True:
        body = {
            "startDate": str(start),
            "endDate":   str(end),
            "dimensions": ["date"],
            "dimensionFilterGroups": [{"filters": filters}],
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


def load_existing(csv_out: Path):
    if not csv_out.exists():
        return {}
    with open(csv_out, newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def fetch_country(key, cfg, access_token, full_refresh):
    csv_out = DATA / cfg["csv"]
    site, country, full_start = cfg["site"], cfg["country"], cfg["full_start"]

    existing = {} if full_refresh else load_existing(csv_out)

    end_date = date.today() - timedelta(days=1)  # yesterday (dataState=all)
    if full_refresh or not existing:
        start_date = full_start
        print(f"  GSC [{key}]: full fetch {start_date} → {end_date}")
    else:
        last = max(existing.keys())
        # Re-fetch last 14 days to catch any GSC revisions
        start_date = max(date.fromisoformat(last) - timedelta(days=14), full_start)
        print(f"  GSC [{key}]: incremental {start_date} → {end_date}  (last on file: {last})")

    if start_date > end_date:
        print(f"  GSC [{key}]: already up to date.")
        return

    rows = query_gsc(access_token, site, country, start_date, end_date)
    if rows is None:
        print(f"  ! GSC [{key}] fetch failed — keeping existing CSV.")
        return

    print(f"  GSC [{key}] API: {len(rows)} rows returned")

    if not rows:
        print(f"  ! GSC [{key}]: no data returned — check site access for {site}")
        return

    for row in rows:
        existing[row["date"]] = row

    sorted_rows = sorted(existing.values(), key=lambda r: r["date"])
    with open(csv_out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "impressions", "clicks"])
        writer.writeheader()
        writer.writerows(sorted_rows)

    print(f"  ✓ {cfg['csv']}: {len(sorted_rows)} days "
          f"({sorted_rows[0]['date']} → {sorted_rows[-1]['date']})")


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
        print("  Keeping existing GSC CSVs unchanged.")
        return

    for key, cfg in COUNTRIES.items():
        fetch_country(key, cfg, access_token, full_refresh)


if __name__ == "__main__":
    main()
