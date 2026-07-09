#!/usr/bin/env python3
"""
Fetch brand keyword impressions from GSC (query dimension) for India,
Australia and UAE, and classify into categories using classifier.py.
Writes data/YYYY-MM.csv (India, unchanged) and data/{au,uae}_YYYY-MM.csv.

Run:
  python3 fetch_gsc_keywords.py           # incremental: last 2 months + any gaps, all countries
  python3 fetch_gsc_keywords.py --full    # all available GSC history, all countries
"""

import os, csv, sys, requests
from datetime import date, timedelta
from calendar import monthrange
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from classifier import classify_keyword

DATA        = Path("data")
BRAND_REGEX = r"car 24|cars24|cars 24|24 car|cara 24|carz 24|card24|car24|24 cars"
TOKEN_URL   = "https://oauth2.googleapis.com/token"

# India is a URL-prefix property needing a country filter; AU/UAE are their
# own ccTLD domain properties (already country-scoped). File prefix is ""
# for India (keeps the existing data/YYYY-MM.csv naming untouched) and
# "au_"/"uae_" for the others so they don't collide with India's files.
COUNTRIES = {
    "india": {"site": "https://www.cars24.com/", "country": "ind", "prefix": "",
              "full_months_back": 16},
    "au":    {"site": "sc-domain:cars24.com.au",  "country": None,  "prefix": "au_",
              "full_months_back": 16},
    "uae":   {"site": "sc-domain:cars24.ae",      "country": None,  "prefix": "uae_",
              "full_months_back": 16},
}


def _load_env():
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_token():
    resp = requests.post(TOKEN_URL, data={
        "client_id":     os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GSC_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    })
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"Token refresh failed: {resp.text[:200]}")
    return token


def fetch_month_queries(token, site, country, year, month):
    """Return list of {keyword, impressions} for a given month/site, brand regex."""
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end   = min(date(year, month, last_day), date.today() - timedelta(days=1))
    if start > end:
        return []

    gsc_url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(site, safe='')}/searchAnalytics/query"
    filters = [{"dimension": "query", "operator": "includingRegex", "expression": BRAND_REGEX}]
    if country:
        filters.insert(0, {"dimension": "country", "operator": "equals", "expression": country})

    all_rows, start_row = [], 0
    while True:
        body = {
            "startDate":  str(start),
            "endDate":    str(end),
            "dimensions": ["query"],
            "dimensionFilterGroups": [{"filters": filters}],
            "rowLimit":  25000,
            "startRow":  start_row,
            "dataState": "all",
        }
        r = requests.post(gsc_url,
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                          json=body)
        if r.status_code != 200:
            print(f"  ! GSC API {r.status_code} for {year}-{month:02d}: {r.text[:200]}")
            return None
        rows = r.json().get("rows", [])
        if not rows:
            break
        for row in rows:
            all_rows.append({"keyword": row["keys"][0], "impressions": int(row.get("impressions", 0))})
        if len(rows) < 25000:
            break
        start_row += 25000

    return all_rows


def write_csv(prefix, year, month, query_rows):
    month_str = f"{year}-{month:02d}"
    out = DATA / f"{prefix}{month_str}.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "impressions", "category", "month"])
        w.writeheader()
        for row in sorted(query_rows, key=lambda r: -r["impressions"]):
            w.writerow({
                "keyword":     row["keyword"],
                "impressions": row["impressions"],
                "category":    classify_keyword(row["keyword"]),
                "month":       month_str,
            })
    total = sum(r["impressions"] for r in query_rows)
    print(f"  ✓ {out.name}: {len(query_rows)} keywords · {total/1e5:.2f}L impressions")


def months_range(from_y, from_m, to_y, to_m):
    y, m = from_y, from_m
    while (y, m) <= (to_y, to_m):
        yield y, m
        m += 1
        if m == 13:
            m, y = 1, y + 1


def fetch_country_keywords(key, cfg, token, full_refresh, last_y, last_m):
    site, country, prefix = cfg["site"], cfg["country"], cfg["prefix"]

    if full_refresh:
        cutoff = date.today().replace(day=1) - timedelta(days=cfg["full_months_back"] * 30)
        to_fetch = list(months_range(cutoff.year, cutoff.month, last_y, last_m))
    else:
        existing = set()
        for f in DATA.glob(f"{prefix}20*.csv"):
            stem = f.stem[len(prefix):] if prefix else f.stem
            try:
                y, m = stem.split("-")
                existing.add((int(y), int(m)))
            except Exception:
                pass

        to_fetch = set()
        for delta in range(1, 3):
            d = date.today().replace(day=1) - timedelta(days=delta * 28)
            to_fetch.add((d.year, d.month))
        if existing:
            first_y, first_m = min(existing)
            for y, m in months_range(first_y, first_m, last_y, last_m):
                if (y, m) not in existing:
                    to_fetch.add((y, m))
        to_fetch = sorted(to_fetch)

    if not to_fetch:
        print(f"  GSC Keywords [{key}]: nothing to fetch")
        return

    print(f"  GSC Keywords [{key}]: fetching {len(to_fetch)} month(s): "
          f"{to_fetch[0][0]}-{to_fetch[0][1]:02d} → {to_fetch[-1][0]}-{to_fetch[-1][1]:02d}")

    for (y, m) in to_fetch:
        rows = fetch_month_queries(token, site, country, y, m)
        if rows is None:
            continue
        if not rows:
            print(f"  - [{key}] {y}-{m:02d}: no data returned")
            continue
        write_csv(prefix, y, m, rows)


def main():
    full_refresh = "--full" in sys.argv
    DATA.mkdir(exist_ok=True)
    _load_env()

    token = get_token()
    today = date.today()

    # Never include the current partial month in keyword CSVs
    prev_end = today.replace(day=1) - timedelta(days=1)  # last day of previous month
    last_y, last_m = prev_end.year, prev_end.month

    for key, cfg in COUNTRIES.items():
        fetch_country_keywords(key, cfg, token, full_refresh, last_y, last_m)


if __name__ == "__main__":
    main()
