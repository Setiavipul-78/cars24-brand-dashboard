#!/usr/bin/env python3
"""
Fetch Australia influencer data from two tabs of the AU influencer tracker
sheet: "Pan Australia POA - Instagram" (per-post creator detail — name,
followers, views, monthly spend) and "Reachouts" (creator partnership
terms still being negotiated), writing data/influencers_au.csv and
data/influencers_au_creators.csv respectively.

Uses the same read-only Sheets OAuth token as fetch_bsos_sheets.py /
fetch_gindex_sheets.py (SHEETS_REFRESH_TOKEN — set up once via
setup_sheets_auth.py).

Sheet: 1VDcKBUNwFacleZFdN_By-qAeroheo3mlqOItat1ZQM8

"Pan Australia POA - Instagram" mirrors the same template UAE's influencer
sheet already uses ("Pan UAE POA - Instagram") — unlike the older
"Previous Efforts" tab (post link + views only, no creator identity) this
one has a creator Name + Followers on every row, which is what actually
lets the AU Influencers tab show a per-creator breakdown instead of an
anonymous post list. Its Views/Likes/Comments/Shares/Saves columns are
present but unpopulated for AU (UAE's equivalent tab does have them
filled in) — only Name/Followers/Avg Views/Final Cost/Avg CPV are used.
"Reachouts" is a separate, mostly-prospecting log (most rows are
"Hold"/"Dropped"/no terms agreed yet) — only rows with a populated
"Total Cost in AUD" represent an actual negotiated creator partnership,
so only those are kept, as a supplementary "deals in progress" table.

Layout quirks handled here:
  - Every row has its own "Live Month" value (no carrying-forward needed,
    unlike "Previous Efforts"), but "Final Cost"/"Avg CPV" are still a
    MONTHLY aggregate recorded on only one row per month (the rest blank
    or "NA") — carried forward onto every row of that month in the CSV
    output so downstream aggregation is a simple group-by.
  - "Avg Views" (despite the name) holds each post's actual view count,
    matching "Previous Efforts"' per-post views exactly where both exist.
  - Numbers use inconsistent comma grouping and a "$"/"AUD" prefix —
    stripped before parsing.

Run:
  python3 fetch_influencers_au.py
"""

import os
import csv
import re
import requests
from pathlib import Path

DATA = Path("data")
SHEET = "1VDcKBUNwFacleZFdN_By-qAeroheo3mlqOItat1ZQM8"
TAB = "Pan Australia POA - Instagram"
TOKEN_URL = "https://oauth2.googleapis.com/token"

MIN_ROW_RATIO = 0.7  # abort if new fetch has fewer than 70% of the previous file's rows


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


def parse_number(raw):
    if raw is None:
        return None
    s = str(raw).replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_cost(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.upper() in ("N/A", "NA"):
        return None
    s = re.sub(r"[^\d.]", "", s)  # strip "$", "AUD", commas, whitespace
    return float(s) if s else None


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


def build_pan_australia_poa(token):
    rows = fetch_values(token, f"'{TAB}'!A1:N2000")
    hdr = next((i for i, r in enumerate(rows) if r and r[0].strip() == "Live Month"), None)
    if hdr is None:
        raise ValidationError(f"{TAB}: could not find 'Live Month' header row")

    parsed = []
    for r in rows[hdr + 1:]:
        if len(r) <= 2 or not r[2].strip():
            continue  # no creator name — blank template row
        month = r[0].strip() if len(r) > 0 else ""
        if not month:
            raise ValidationError(f"{TAB}: data row with no Live Month: {r!r}")
        parsed.append({
            "month":      month,
            "creator":    r[2].strip(),
            "followers":  r[5].strip() if len(r) > 5 else "",
            "views":      parse_number(r[6]) if len(r) > 6 else None,   # "Avg Views" col holds per-post views
            "cost_aud":   parse_cost(r[7]) if len(r) > 7 else None,      # "Final Cost" col, one row per month
            "status":     r[9].strip() if len(r) > 9 else "",
            "video_link": r[13].strip() if len(r) > 13 else "",
        })
    if not parsed:
        raise ValidationError(f"{TAB}: zero data rows parsed")

    # "Final Cost" is a monthly aggregate recorded once per month — carry
    # it forward onto every row of that month for a simple downstream group-by.
    month_cost = {}
    for p in parsed:
        if p["cost_aud"] is not None:
            month_cost[p["month"]] = p["cost_aud"]
    out = [{**p, "cost_aud": month_cost.get(p["month"], "")} for p in parsed]

    path = DATA / "influencers_au.csv"
    check_row_count(len(out), path, "AU influencers (Pan Australia POA)")
    DATA.mkdir(exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["month", "creator", "followers", "views", "cost_aud", "status", "video_link"])
        w.writeheader()
        w.writerows(out)
    months = sorted(set(r["month"] for r in out), key=lambda m: out.index(next(x for x in out if x["month"] == m)))
    print(f"  ✓ influencers_au.csv: {len(out)} posts across {len(months)} months ({months[0]} → {months[-1]})")


def build_reachouts(token):
    rows = fetch_values(token, "Reachouts!A1:L300")
    if not rows or [c.strip() for c in rows[0][:3]] != ["", "Category", "Channel Name"]:
        raise ValidationError("Reachouts: unexpected header row — sheet layout may have changed")

    out = []
    for r in rows[1:]:
        if len(r) <= 10 or not r[10].strip():
            continue  # no agreed "Total Cost in AUD" yet — still just a prospect, not a real deal
        out.append({
            "platform":     r[0].strip() if len(r) > 0 else "",
            "category":     r[1].strip() if len(r) > 1 else "",
            "creator":      r[2].strip() if len(r) > 2 else "",
            "followers":    r[3].strip() if len(r) > 3 else "",
            "link":         r[4].strip() if len(r) > 4 else "",
            "recent_views": parse_number(r[5]) if len(r) > 5 else None,
            "status":       r[6].strip() if len(r) > 6 else "",
            "cost_aud":     parse_number(r[10]),
            "cpv_aud":      parse_number(r[11]) if len(r) > 11 else None,
        })

    if not out:
        raise ValidationError("Reachouts: zero rows with an agreed Total Cost found")
    out.sort(key=lambda r: r["cost_aud"], reverse=True)
    path = DATA / "influencers_au_creators.csv"
    check_row_count(len(out), path, "AU influencer creators (Reachouts)")
    DATA.mkdir(exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["platform", "category", "creator", "followers", "link", "recent_views", "status", "cost_aud", "cpv_aud"])
        w.writeheader()
        w.writerows(out)
    print(f"  ✓ influencers_au_creators.csv: {len(out)} creator partnerships with agreed terms")


def main():
    load_env()
    token = get_token()
    print("  Fetching AU influencer data (Pan Australia POA - Instagram)…")
    try:
        build_pan_australia_poa(token)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"  ✗ AU influencers fetch failed validation, existing CSV left untouched: {e}")

    print("  Fetching AU influencer creator partnerships (Reachouts)…")
    try:
        build_reachouts(token)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"  ✗ AU influencer creators fetch failed validation, existing CSV left untouched: {e}")


if __name__ == "__main__":
    main()
