#!/usr/bin/env python3
"""
Fetch Australia influencer campaign data from the "Previous Efforts" tab of
the AU influencer tracker sheet, and write it into data/influencers_au.csv.

Uses the same read-only Sheets OAuth token as fetch_bsos_sheets.py /
fetch_gindex_sheets.py (SHEETS_REFRESH_TOKEN — set up once via
setup_sheets_auth.py).

Sheet: 1VDcKBUNwFacleZFdN_By-qAeroheo3mlqOItat1ZQM8, tab "Previous Efforts"

Only "Previous Efforts" is used — the sheet's other tabs (Reachouts, Google
Data, Marketplaces, Universe Mapping) are creator-prospecting/research
trackers, not campaign results, per an explicit instruction to only use
Previous Efforts.

Layout quirks handled here:
  - Column A (Month) is only filled on each month's first row; blank on
    every row after that until the next month starts — carried forward.
  - Column E (cost, "$X,XXX.XX AUD" or "N/A") is a MONTHLY total, only on
    each month's first row — also carried forward onto every row of CSV
    output so downstream aggregation is a simple group-by.
  - Each month ends with a subtotal row (blank serial no + blank link,
    just a summed views figure) — skipped; monthly view totals are instead
    computed by summing the real per-post rows, not trusted from the sheet.
  - Column F ("CTM") holds free-text remarks (e.g. "*manual scouting was
    halted."), not a second cost column — ignored.
  - Numbers use inconsistent comma grouping (e.g. "2,29,939") — stripping
    all commas before parsing works regardless of grouping style.
  - Some trailing rows have a serial no but no link/views yet (future
    placeholders) — skipped, since a real post row needs both a link and a
    views count.

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
TAB = "Previous Efforts"
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
    if not s or s.upper() == "N/A":
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


def build_previous_efforts(token):
    rows = fetch_values(token, f"'{TAB}'!A1:F2000")
    hdr = next((i for i, r in enumerate(rows) if r and r[0].strip() == "Month"), None)
    if hdr is None:
        raise ValidationError(f"{TAB}: could not find 'Month' header row")

    out = []
    current_month, current_cost = None, None
    for r in rows[hdr + 1:]:
        if not r:
            continue
        month_cell = r[0].strip() if len(r) > 0 else ""
        link = r[2].strip() if len(r) > 2 else ""
        views = parse_number(r[3]) if len(r) > 3 else None
        if month_cell:
            current_month = month_cell
            current_cost = parse_cost(r[4]) if len(r) > 4 else None
        if not link or views is None:
            continue  # subtotal row, or a future placeholder row with no data yet
        if not current_month:
            raise ValidationError(f"{TAB}: data row before any month header seen: {r!r}")
        out.append({"month": current_month, "link": link, "views": views,
                     "cost_aud": current_cost if current_cost is not None else ""})

    if not out:
        raise ValidationError(f"{TAB}: zero data rows parsed")
    path = DATA / "influencers_au.csv"
    check_row_count(len(out), path, "AU influencers (Previous Efforts)")
    DATA.mkdir(exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["month", "link", "views", "cost_aud"])
        w.writeheader()
        w.writerows(out)
    months = sorted(set(r["month"] for r in out), key=lambda m: out.index(next(x for x in out if x["month"] == m)))
    print(f"  ✓ influencers_au.csv: {len(out)} posts across {len(months)} months ({months[0]} → {months[-1]})")


def main():
    load_env()
    token = get_token()
    print("  Fetching AU influencer data (Previous Efforts)…")
    try:
        build_previous_efforts(token)
    except (ValidationError, ValueError, KeyError) as e:
        print(f"  ✗ AU influencers fetch failed validation, existing CSV left untouched: {e}")


if __name__ == "__main__":
    main()
