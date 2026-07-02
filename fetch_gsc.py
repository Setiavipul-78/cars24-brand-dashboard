#!/usr/bin/env python3
"""
Fetch Google Search Console brand search impressions for India.
Requires GSC_SERVICE_ACCOUNT_JSON in environment (raw JSON string).

Setup:
  1. GCP Console → APIs & Services → Enable "Google Search Console API"
  2. IAM & Admin → Service Accounts → Create → Download JSON key
  3. GSC → Settings → Users & permissions → Add service-account email (Restricted)
  4. Set GSC_SERVICE_ACCOUNT_JSON=<contents of JSON file> in .env + GitHub Secrets

Run manually:
  python3 fetch_gsc.py
  python3 fetch_gsc.py --full    # re-fetch full history from Nov 2023
"""

import os
import sys
import json
import csv
from datetime import date, timedelta
from pathlib import Path

DATA    = Path("data")
SITE    = "https://www.cars24.com/"
CSV_OUT = DATA / "gsc_daily_india.csv"

# Regex matching Cars24 brand queries (same filter as your GSC console)
# Matches: cars24, car24, cars 24, car 24, cars-24, etc.
BRAND_REGEX = r"cars?\s?24|car24"


def get_service():
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        print("  ! GSC_SERVICE_ACCOUNT_JSON not set — skipping GSC API fetch")
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        return build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    except ImportError:
        print("  ! Missing packages: pip install google-api-python-client google-auth")
        return None
    except json.JSONDecodeError as e:
        print(f"  ! GSC_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
        return None
    except Exception as e:
        print(f"  ! GSC auth failed: {e}")
        return None


def load_existing():
    if not CSV_OUT.exists():
        return {}
    with open(CSV_OUT, newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def query_gsc(service, start: date, end: date):
    """Query GSC searchAnalytics for brand impressions in India by date."""
    all_rows = []
    # GSC API max 25 000 rows; paginate just in case
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
            "rowLimit":   25000,
            "startRow":   start_row,
            "dataState":  "final"
        }
        resp = service.searchanalytics().query(siteUrl=SITE, body=body).execute()
        rows = resp.get("rows", [])
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


def main():
    full_refresh = "--full" in sys.argv
    DATA.mkdir(exist_ok=True)

    service = get_service()
    if not service:
        print("  Keeping existing gsc_daily_india.csv unchanged.")
        return

    existing = load_existing()

    # Date range to fetch
    end_date = date.today() - timedelta(days=2)  # GSC data lag ~2 days
    if full_refresh or not existing:
        start_date = date(2023, 11, 1)
        print(f"  GSC: full fetch {start_date} → {end_date}")
    else:
        last = max(existing.keys())
        # Re-fetch last 14 days to catch GSC data updates
        start_date = max(
            date.fromisoformat(last) - timedelta(days=14),
            date(2023, 11, 1)
        )
        print(f"  GSC: incremental fetch {start_date} → {end_date} (last on file: {last})")

    if start_date > end_date:
        print(f"  GSC: already up to date (end_date {end_date} ≤ start_date)")
        return

    rows = query_gsc(service, start_date, end_date)
    print(f"  GSC API: {len(rows)} rows returned")

    if not rows:
        print("  ! No data returned — check service account permissions and GSC property")
        return

    # Merge API results into existing
    for row in rows:
        existing[row["date"]] = row

    # Write sorted CSV
    sorted_rows = sorted(existing.values(), key=lambda r: r["date"])
    with open(CSV_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "impressions", "clicks"])
        writer.writeheader()
        writer.writerows(sorted_rows)

    print(f"  ✓ gsc_daily_india.csv: {len(sorted_rows)} days total "
          f"({sorted_rows[0]['date']} → {sorted_rows[-1]['date']})")


if __name__ == "__main__":
    main()
