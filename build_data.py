#!/usr/bin/env python3
"""
Build data.json for the Cars24 static HTML dashboard.
Run: python3 build_data.py
"""

import json, math, sys, calendar
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA = Path("data")
OUT  = Path("data.json")

# ── Utilities ─────────────────────────────────────────────────────────────────
def sf(v):
    """Safe float: return None for NaN/None, else float."""
    if v is None: return None
    try:
        f = float(v)
        return None if math.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None

def pct_ch(curr, prev):
    if prev is None or curr is None or prev == 0: return None
    try: return round((curr - prev) / abs(prev) * 100, 2)
    except: return None

def pp_ch(curr, prev):
    if curr is None or prev is None: return None
    try: return round(curr - prev, 3)
    except: return None

def mlabel(m):
    try: return pd.Period(m, freq="M").strftime("%b'%y")
    except: return str(m)

def fmt_lakh(n):
    if n is None: return "—"
    return f"{n/1e5:.2f}L"

# ── Monthly Impressions (GSC) ─────────────────────────────────────────────────
def build_monthly():
    p = DATA / "historical_totals.csv"
    if not p.exists():
        print("  ⚠ historical_totals.csv missing"); return []
    df = pd.read_csv(p).sort_values("month").reset_index(drop=True)

    # Auto-extend with months from gsc_daily_india.csv not yet in historical_totals
    gsc_p = DATA / "gsc_daily_india.csv"
    if gsc_p.exists():
        gsc = pd.read_csv(gsc_p)
        gsc["date"]  = pd.to_datetime(gsc["date"])
        gsc["month"] = gsc["date"].dt.to_period("M").astype(str)
        # Only consider complete months (not the current partial month)
        today_period = str(pd.Timestamp("today").to_period("M"))
        known = set(df["month"].tolist())
        monthly_agg = (gsc[gsc["month"] != today_period]
                       .groupby("month")["impressions"].sum().reset_index()
                       .rename(columns={"impressions": "total_impressions"}))
        new_months = monthly_agg[~monthly_agg["month"].isin(known)].copy()
        if not new_months.empty:
            new_months["mom_pct"] = None
            new_months["yoy_pct"] = None
            df = pd.concat([df, new_months[["month","total_impressions","mom_pct","yoy_pct"]]]
                           ).sort_values("month").reset_index(drop=True)
            print(f"  + Extended monthly with {len(new_months)} GSC months: "
                  f"{new_months['month'].tolist()}")

    rows = []
    for i, row in df.iterrows():
        prev_imp = float(df.iloc[i-1]["total_impressions"]) if i > 0 else None
        yoy_m = str(pd.Period(row["month"], freq="M") - 12)
        yoy_r = df[df["month"] == yoy_m]
        yoy_imp = float(yoy_r["total_impressions"].iloc[0]) if not yoy_r.empty else None
        rows.append({
            "month":     row["month"],
            "label":     mlabel(row["month"]),
            "impressions": int(row["total_impressions"]),
            "imp_lakh":  round(float(row["total_impressions"]) / 1e5, 2),
            "mom":       pct_ch(float(row["total_impressions"]), prev_imp),
            "yoy":       pct_ch(float(row["total_impressions"]), yoy_imp),
        })
    return rows

# ── BSOS Monthly ──────────────────────────────────────────────────────────────
def _drop_incomplete_trailing_months(df, daily_csv_name, label):
    """Drop trailing month rows not yet fully covered by the daily feed.

    Brandstack's own "Month" tab can get a row added for the current month
    before that month has been tracked day-by-day for its full length — which
    would otherwise show a partial-month average (e.g. 8 days of June) as if
    it were the complete month's figure. We only trust a month once the daily
    feed has (nearly) every calendar day for it — checked fresh on every run,
    so this applies to whichever month is actually latest, not just today's.
    """
    if "month" not in df.columns or not len(df):
        return df
    daily_p = DATA / daily_csv_name
    if not daily_p.exists():
        return df
    ddf = pd.read_csv(daily_p)
    if "date" not in ddf.columns:
        return df
    ddf["date"] = pd.to_datetime(ddf["date"])
    day_counts = ddf.groupby(ddf["date"].dt.to_period("M").astype(str)).size()

    def is_complete(m):
        have = day_counts.get(m, 0)
        if have == 0:
            return True  # no daily coverage to check against — trust the monthly row as-is
        try:
            year, mo = int(m[:4]), int(m[5:7])
            days_in_month = calendar.monthrange(year, mo)[1]
        except Exception:
            return True
        return have >= days_in_month - 1  # allow ~1 day of reporting lag

    while len(df) and not is_complete(df.iloc[-1]["month"]):
        dropped = df.iloc[-1]["month"]
        have = day_counts.get(dropped, 0)
        df = df.iloc[:-1]
        print(f"  ⚠ BSOS monthly ({label}): excluding {dropped} — only {have} day(s) "
              f"tracked in the daily feed so far, not a full month yet")
    return df

def build_bsos_monthly():
    for fname in ["bsos_pan_monthly.csv", "bsos_india_5b_daily.csv", "bsos_india_daily.csv"]:
        p = DATA / fname
        if not p.exists(): continue
        df = pd.read_csv(p)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.to_period("M").astype(str)
            bc = [c for c in df.columns if c not in ("date","month")]
            df = df.groupby("month")[bc].mean().reset_index()
        df = df.sort_values("month").reset_index(drop=True)
        df = _drop_incomplete_trailing_months(df, "bsos_pan_india_daily.csv", "pan-India")
        bc = [c for c in df.columns if c != "month"]
        rows = []
        for i, row in df.iterrows():
            pr = df.iloc[i-1] if i > 0 else None
            r = {"month": row["month"], "label": mlabel(row["month"])}
            for b in bc:
                v = sf(row.get(b))
                r[b] = v
                r[f"{b}_mom"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
            rows.append(r)
        print(f"  ✓ BSOS monthly from {fname}: {len(rows)} months")
        return rows
    print("  ⚠ No BSOS monthly source found"); return []

# ── BSOS Weekly ───────────────────────────────────────────────────────────────
def build_bsos_weekly():
    for fname in ["bsos_pan_weekly.csv", "bsos_india_5b_daily.csv", "bsos_india_daily.csv"]:
        p = DATA / fname
        if not p.exists(): continue
        df = pd.read_csv(p)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df["ws"] = df["date"].dt.to_period("W-SAT").apply(lambda x: x.start_time)  # Sunday-start weeks, matches BSOS sheet convention
            bc = [c for c in df.columns if c not in ("date","ws","week","week_start")]
            df = df.groupby("ws")[bc].mean().reset_index()
            df["ws"] = pd.to_datetime(df["ws"])
            df["week"] = df["ws"].apply(
                lambda s: f"{s.strftime('%d %b')} – {(s + pd.Timedelta(6,'d')).strftime('%d %b %Y')}"
            )
        else:
            if "week_start" in df.columns:
                df["ws"] = pd.to_datetime(df["week_start"])
            bc = [c for c in df.columns if c not in ("ws","week_start","week")]
        df = df.sort_values("ws").reset_index(drop=True)
        rows = []
        for i, row in df.iterrows():
            pr = df.iloc[i-1] if i > 0 else None
            r = {
                "week_start": pd.Timestamp(row["ws"]).strftime("%Y-%m-%d"),
                "week": row.get("week","")
            }
            for b in bc:
                v = sf(row.get(b))
                r[b] = v
                r[f"{b}_wow"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
            rows.append(r)
        rows = rows[-26:]
        print(f"  ✓ BSOS weekly from {fname}: {len(rows)} weeks")
        return rows
    return []

# ── BSOS Daily ────────────────────────────────────────────────────────────────
def build_bsos_daily():
    for fname in ["bsos_pan_india_daily.csv", "bsos_india_5b_daily.csv", "bsos_india_daily.csv"]:
        p = DATA / fname
        if not p.exists(): continue
        df = pd.read_csv(p)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        bc = [c for c in df.columns if c != "date"]
        rows = []
        for _, row in df.iterrows():
            r = {"date": row["date"].strftime("%Y-%m-%d")}
            for b in bc:
                r[b] = sf(row.get(b))
            rows.append(r)
        rows = rows[-180:]
        print(f"  ✓ BSOS daily from {fname}: {len(rows)} days")
        return rows
    return []

# ── City BSOS ─────────────────────────────────────────────────────────────────
def _city_monthly(grp, bc):
    monthly = grp.groupby("month")[bc].mean().reset_index().sort_values("month").reset_index(drop=True)
    rows = []
    for i, row in monthly.iterrows():
        pr = monthly.iloc[i-1] if i > 0 else None
        r = {"month": row["month"], "label": mlabel(row["month"])}
        for b in bc:
            v = sf(row.get(b))
            r[b] = v
            r[f"{b}_mom"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
        rows.append(r)
    return rows

def _city_weekly(grp, bc):
    g = grp.copy()
    g["ws"] = g["date"].dt.to_period("W-SAT").apply(lambda x: x.start_time)  # Sunday-start weeks, matches BSOS sheet convention
    weekly = g.groupby("ws")[bc].mean().reset_index().sort_values("ws").reset_index(drop=True)
    rows = []
    for i, row in weekly.iterrows():
        pr = weekly.iloc[i-1] if i > 0 else None
        ws = pd.Timestamp(row["ws"])
        r = {
            "week_start": ws.strftime("%Y-%m-%d"),
            "week": f"{ws.strftime('%d %b')} – {(ws + pd.Timedelta(6,'d')).strftime('%d %b %Y')}",
        }
        for b in bc:
            v = sf(row.get(b))
            r[b] = v
            r[f"{b}_wow"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
        rows.append(r)
    return rows[-26:]

def _city_daily(grp, bc):
    daily = grp.sort_values("date").reset_index(drop=True)
    rows = []
    for _, row in daily.iterrows():
        r = {"date": row["date"].strftime("%Y-%m-%d")}
        for b in bc:
            r[b] = sf(row.get(b))
        rows.append(r)
    return rows[-180:]

def build_bsos_cities():
    p = DATA / "bsos_city_daily.csv"
    if not p.exists():
        print("  ⚠ bsos_city_daily.csv missing"); return {}
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    bc = [c for c in df.columns if c not in ("date","city","month")]
    result = {}
    for city, grp in df.groupby("city"):
        result[city] = {
            "monthly": _city_monthly(grp, bc),
            "weekly":  _city_weekly(grp, bc),
            "daily":   _city_daily(grp, bc),
        }
    print(f"  ✓ City BSOS: {len(result)} cities (monthly + weekly + daily)")
    return result

# ── GSC Daily ─────────────────────────────────────────────────────────────────
def build_gsc_daily():
    p = DATA / "gsc_daily_india.csv"
    if not p.exists():
        print("  ⚠ gsc_daily_india.csv missing"); return []
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    rows = []
    for i, row in df.iterrows():
        prev_imp = int(df.iloc[i-1]["impressions"]) if i > 0 else None
        rows.append({
            "date":        row["date"].strftime("%Y-%m-%d"),
            "impressions": int(row["impressions"]),
            "clicks":      int(row["clicks"]) if "clicks" in row and pd.notna(row["clicks"]) else 0,
            "dod":         pct_ch(int(row["impressions"]), prev_imp),
            "weekend":     row["date"].weekday() >= 5,
        })
    print(f"  ✓ GSC daily: {len(rows)} days")
    return rows

# ── GSC Weekly ────────────────────────────────────────────────────────────────
def build_gsc_weekly():
    p = DATA / "gsc_daily_india.csv"
    if not p.exists():
        print("  ⚠ gsc_daily_india.csv missing (weekly skipped)"); return []
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    # Week starts Monday
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    weekly = df.groupby("week_start").agg(impressions=("impressions","sum"), clicks=("clicks","sum")).reset_index()
    weekly = weekly.sort_values("week_start").reset_index(drop=True)
    rows = []
    for i, row in weekly.iterrows():
        prev = int(weekly.iloc[i-1]["impressions"]) if i > 0 else None
        ws = row["week_start"]
        we = ws + pd.Timedelta(days=6)
        rows.append({
            "week_start": ws.strftime("%Y-%m-%d"),
            "week_label": f"{ws.strftime('%d %b')} – {we.strftime('%d %b %y')}",
            "impressions": int(row["impressions"]),
            "clicks":      int(row.get("clicks", 0) or 0),
            "wow":         pct_ch(int(row["impressions"]), prev),
        })
    print(f"  ✓ GSC weekly: {len(rows)} weeks")
    return rows

# ── Google Search Index (Trends-style 0-100 index, not a % share) ─────────────
def build_gindex():
    pan_p = DATA / "gindex_pan_monthly.csv"
    if not pan_p.exists():
        print("  ⚠ gindex_pan_monthly.csv missing (Google Index tab will be empty)")
        return {"monthly": [], "city_brand": {}, "city_generic": {}}

    # Exclude the current calendar month if it has landed but isn't finished yet —
    # same convention as build_monthly()'s GSC auto-extend.
    today_period = str(pd.Timestamp("today").to_period("M"))

    df = pd.read_csv(pan_p).sort_values("month").reset_index(drop=True)
    df = df[df["month"] != today_period].reset_index(drop=True)
    bc = [c for c in df.columns if c != "month"]
    monthly = []
    for i, row in df.iterrows():
        pr = df.iloc[i-1] if i > 0 else None
        r = {"month": row["month"], "label": mlabel(row["month"])}
        for b in bc:
            v = sf(row.get(b))
            r[b] = v
            r[f"{b}_mom"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
        monthly.append(r)

    def load_city_index(fname):
        p = DATA / fname
        if not p.exists():
            return {}
        cdf = pd.read_csv(p).sort_values("month").reset_index(drop=True)
        cdf = cdf[cdf["month"] != today_period].reset_index(drop=True)
        cities = [c for c in cdf.columns if c != "month"]
        result = {}
        for city in cities:
            rows = []
            for i, row in cdf.iterrows():
                pr = cdf.iloc[i-1] if i > 0 else None
                v = sf(row.get(city))
                rows.append({
                    "month": row["month"], "label": mlabel(row["month"]),
                    "index": v,
                    "index_mom": pp_ch(v, sf(pr.get(city)) if pr is not None else None),
                })
            result[city] = rows
        return result

    city_brand   = load_city_index("gindex_city_brand_monthly.csv")
    city_generic = load_city_index("gindex_city_generic_monthly.csv")

    print(f"  ✓ Google Index: {len(monthly)} months (pan-India) | "
          f"{len(city_brand)} cities (brand) | {len(city_generic)} cities (generic)")
    return {"monthly": monthly, "city_brand": city_brand, "city_generic": city_generic}

# ── BSOS for AU / UAE (dedicated Brandstack sheets, separate competitor sets
# from India's — see fetch_bsos_intl.py) ────────────────────────────────────
def build_bsos_monthly_from(csv_name):
    p = DATA / csv_name
    if not p.exists(): return []
    df = pd.read_csv(p).sort_values("month").reset_index(drop=True)
    bc = [c for c in df.columns if c != "month"]
    rows = []
    for i, row in df.iterrows():
        pr = df.iloc[i-1] if i > 0 else None
        r = {"month": row["month"], "label": mlabel(row["month"])}
        for b in bc:
            v = sf(row.get(b))
            r[b] = v
            r[f"{b}_mom"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
        rows.append(r)
    return rows

def build_bsos_weekly_from(csv_name):
    p = DATA / csv_name
    if not p.exists(): return []
    df = pd.read_csv(p).sort_values("week_start").reset_index(drop=True)
    bc = [c for c in df.columns if c not in ("week_start","week")]
    rows = []
    for i, row in df.iterrows():
        pr = df.iloc[i-1] if i > 0 else None
        r = {"week_start": row["week_start"], "week": row.get("week","")}
        for b in bc:
            v = sf(row.get(b))
            r[b] = v
            r[f"{b}_wow"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
        rows.append(r)
    return rows[-26:]

def build_bsos_daily_from(csv_name):
    p = DATA / csv_name
    if not p.exists(): return []
    df = pd.read_csv(p).sort_values("date").reset_index(drop=True)
    bc = [c for c in df.columns if c != "date"]
    rows = []
    for _, row in df.iterrows():
        r = {"date": row["date"]}
        for b in bc:
            r[b] = sf(row.get(b))
        rows.append(r)
    return rows[-180:]

AU_REGION_NAMES = {"NSW": "New South Wales", "QLD": "Queensland", "VIC": "Victoria"}

def build_bsos_regions(monthly_csv, weekly_csv, region_names=None):
    """Region-level BSOS (AUS: NSW/QLD/VIC) -> {region: {"monthly":[...], "weekly":[...]}}
    region_names optionally maps the sheet's own abbreviated block names (e.g.
    Brandstack's "NSW") to a display-friendly full name, so the frontend's
    Object.keys(regions) already shows full state names everywhere with no
    per-call-site translation needed."""
    region_names = region_names or {}
    mp, wp = DATA / monthly_csv, DATA / weekly_csv
    mdf = pd.read_csv(mp) if mp.exists() else pd.DataFrame(columns=["region","month"])
    wdf = pd.read_csv(wp) if wp.exists() else pd.DataFrame(columns=["region","week_start"])
    regions = sorted(set(mdf.get("region", [])) | set(wdf.get("region", [])))
    m_bc = [c for c in mdf.columns if c not in ("region","month")]
    w_bc = [c for c in wdf.columns if c not in ("region","week_start","week")]
    result = {}
    for region in regions:
        m_rows = []
        g = mdf[mdf["region"] == region].sort_values("month").reset_index(drop=True)
        for i, row in g.iterrows():
            pr = g.iloc[i-1] if i > 0 else None
            r = {"month": row["month"], "label": mlabel(row["month"])}
            for b in m_bc:
                v = sf(row.get(b))
                r[b] = v
                r[f"{b}_mom"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
            m_rows.append(r)
        w_rows = []
        g = wdf[wdf["region"] == region].sort_values("week_start").reset_index(drop=True)
        for i, row in g.iterrows():
            pr = g.iloc[i-1] if i > 0 else None
            r = {"week_start": row["week_start"], "week": row.get("week","")}
            for b in w_bc:
                v = sf(row.get(b))
                r[b] = v
                r[f"{b}_wow"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
            w_rows.append(r)
        result[region_names.get(region, region)] = {"monthly": m_rows, "weekly": w_rows[-26:]}
    return result

# ── Google Index for AU / UAE (dedicated sheet tabs, Cars24-only pan index —
# no Category/Generic split like India has) ─────────────────────────────────
def build_gindex_simple(csv_name):
    p = DATA / csv_name
    if not p.exists(): return []
    today_period = str(pd.Timestamp("today").to_period("M"))
    df = pd.read_csv(p).sort_values("month").reset_index(drop=True)
    df = df[df["month"] != today_period].reset_index(drop=True)
    rows = []
    for i, row in df.iterrows():
        pr = df.iloc[i-1] if i > 0 else None
        v = sf(row.get("Cars24"))
        rows.append({
            "month": row["month"], "label": mlabel(row["month"]),
            "Cars24": v,
            "Cars24_mom": pp_ch(v, sf(pr.get("Cars24")) if pr is not None else None),
        })
    return rows

def build_gindex_regions(csv_name):
    """Region-level Google Index (UAE cities / AUS regions) -> {region: [...]}"""
    p = DATA / csv_name
    if not p.exists(): return {}
    today_period = str(pd.Timestamp("today").to_period("M"))
    df = pd.read_csv(p)
    df = df[df["month"] != today_period]
    result = {}
    for region, grp in df.groupby("region"):
        grp = grp.sort_values("month").reset_index(drop=True)
        rows = []
        for i, row in grp.iterrows():
            pr = grp.iloc[i-1] if i > 0 else None
            v = sf(row.get("index"))
            rows.append({
                "month": row["month"], "label": mlabel(row["month"]),
                "index": v,
                "index_mom": pp_ch(v, sf(pr.get("index")) if pr is not None else None),
            })
        result[region] = rows
    return result

def build_country_extras(key):
    """BSOS + Google Index for AU/UAE — dedicated Brandstack/GIndex sheets,
    separate from India's (see fetch_bsos_intl.py, fetch_gindex_sheets.py)."""
    if key == "uae":
        bsos = {
            "monthly": build_bsos_monthly_from("bsos_uae_monthly.csv"),
            "weekly":  build_bsos_weekly_from("bsos_uae_weekly.csv"),
            "daily":   build_bsos_daily_from("bsos_uae_daily.csv"),
            "regions": {},  # no per-city BSOS breakdown for UAE
        }
        gindex = {
            "monthly": build_gindex_simple("gindex_uae_monthly.csv"),
            "regions": build_gindex_regions("gindex_uae_city_monthly.csv"),
        }
    elif key == "au":
        bsos = {
            "monthly": build_bsos_monthly_from("bsos_aus_monthly.csv"),
            "weekly":  build_bsos_weekly_from("bsos_aus_weekly.csv"),
            "daily":   [],  # no Daily tab exists for AUS
            "regions": build_bsos_regions("bsos_aus_region_monthly.csv", "bsos_aus_region_weekly.csv", AU_REGION_NAMES),
        }
        gindex = {
            "monthly": build_gindex_simple("gindex_aus_monthly.csv"),
            "regions": build_gindex_regions("gindex_aus_region_monthly.csv"),
        }
    else:
        return {"bsos": {}, "gindex": {}}
    print(f"  ✓ BSOS [{key}]: {len(bsos['monthly'])} months | {len(bsos['weekly'])} weeks | "
          f"{len(bsos['daily'])} days | {len(bsos['regions'])} regions")
    print(f"  ✓ Google Index [{key}]: {len(gindex['monthly'])} months | {len(gindex['regions'])} regions")
    return {"bsos": bsos, "gindex": gindex}

# ── AU / UAE GSC (same shape as India's daily/weekly/monthly, no historical_totals
# baseline — these countries only have live GSC data, no pre-API history) ──────
def build_monthly_country(csv_name):
    p = DATA / csv_name
    if not p.exists():
        return []
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    today_period = str(pd.Timestamp("today").to_period("M"))
    mon = (df[df["month"] != today_period]
           .groupby("month")["impressions"].sum().reset_index()
           .sort_values("month").reset_index(drop=True))
    rows = []
    for i, row in mon.iterrows():
        prev_imp = float(mon.iloc[i-1]["impressions"]) if i > 0 else None
        yoy_m = str(pd.Period(row["month"], freq="M") - 12)
        yoy_r = mon[mon["month"] == yoy_m]
        yoy_imp = float(yoy_r["impressions"].iloc[0]) if not yoy_r.empty else None
        rows.append({
            "month":     row["month"],
            "label":     mlabel(row["month"]),
            "impressions": int(row["impressions"]),
            "imp_lakh":  round(float(row["impressions"]) / 1e5, 2),
            "mom":       pct_ch(float(row["impressions"]), prev_imp),
            "yoy":       pct_ch(float(row["impressions"]), yoy_imp),
        })
    return rows

def build_gsc_daily_country(csv_name):
    p = DATA / csv_name
    if not p.exists():
        return []
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    rows = []
    for i, row in df.iterrows():
        prev_imp = int(df.iloc[i-1]["impressions"]) if i > 0 else None
        rows.append({
            "date":        row["date"].strftime("%Y-%m-%d"),
            "impressions": int(row["impressions"]),
            "clicks":      int(row["clicks"]) if "clicks" in row and pd.notna(row["clicks"]) else 0,
            "dod":         pct_ch(int(row["impressions"]), prev_imp),
            "weekend":     row["date"].weekday() >= 5,
        })
    return rows

def build_gsc_weekly_country(csv_name):
    p = DATA / csv_name
    if not p.exists():
        return []
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    weekly = df.groupby("week_start").agg(impressions=("impressions","sum"), clicks=("clicks","sum")).reset_index()
    weekly = weekly.sort_values("week_start").reset_index(drop=True)
    rows = []
    for i, row in weekly.iterrows():
        prev = int(weekly.iloc[i-1]["impressions"]) if i > 0 else None
        ws = row["week_start"]
        we = ws + pd.Timedelta(days=6)
        rows.append({
            "week_start": ws.strftime("%Y-%m-%d"),
            "week_label": f"{ws.strftime('%d %b')} – {we.strftime('%d %b %y')}",
            "impressions": int(row["impressions"]),
            "clicks":      int(row.get("clicks", 0) or 0),
            "wow":         pct_ch(int(row["impressions"]), prev),
        })
    return rows

def build_keywords_country(prefix):
    files = sorted(DATA.glob(f"{prefix}20*.csv"))
    if not files:
        return {"monthly": [], "categories": [], "cat_months": [], "cat_matrix": []}
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if "impressions" in df.columns and "category" in df.columns:
                month = f.stem[len(prefix):] if prefix else f.stem
                df["month"] = month
                dfs.append(df[["keyword","category","impressions","month"]])
        except Exception as e:
            print(f"  ⚠ Skipping {f.name}: {e}")
    if not dfs:
        return {"monthly": [], "categories": [], "cat_months": [], "cat_matrix": []}
    kw = pd.concat(dfs, ignore_index=True)
    kw["impressions"] = pd.to_numeric(kw["impressions"], errors="coerce").fillna(0)

    mon = kw.groupby("month")["impressions"].sum().reset_index().sort_values("month").reset_index(drop=True)
    mon_rows = []
    for i, row in mon.iterrows():
        pr = mon.iloc[i-1] if i > 0 else None
        yoy_m = str(pd.Period(row["month"], freq="M") - 12)
        yoy_r = mon[mon["month"] == yoy_m]
        yoy_v = float(yoy_r["impressions"].iloc[0]) if not yoy_r.empty else None
        mon_rows.append({
            "month": row["month"],
            "label": mlabel(row["month"]),
            "impressions": int(row["impressions"]),
            "imp_lakh": round(float(row["impressions"]) / 1e5, 2),
            "mom": pct_ch(float(row["impressions"]), float(pr["impressions"]) if pr is not None else None),
            "yoy": pct_ch(float(row["impressions"]), yoy_v),
        })

    latest_m = mon["month"].max()
    cat_df = kw[kw["month"] == latest_m].groupby("category")["impressions"].sum().reset_index()
    total_cat = cat_df["impressions"].sum()
    cat_df["share"] = (cat_df["impressions"] / total_cat * 100).round(1) if total_cat else 0
    cat_df = cat_df.sort_values("impressions", ascending=False)
    prev_m_cats = sorted(kw["month"].unique())
    prev_m_cats = [m for m in prev_m_cats if m < latest_m]
    prev_m = prev_m_cats[-1] if prev_m_cats else None
    cat_prev = {}
    if prev_m:
        cp = kw[kw["month"] == prev_m].groupby("category")["impressions"].sum().to_dict()
        prev_total = sum(cp.values())
        cat_prev = {k: {"imp": v, "share": v/prev_total*100 if prev_total else 0} for k,v in cp.items()}

    cat_rows = []
    for _, row in cat_df.iterrows():
        cat = row["category"]
        prev = cat_prev.get(cat, {})
        cat_rows.append({
            "category":   cat,
            "impressions": int(row["impressions"]),
            "imp_lakh":   round(float(row["impressions"])/1e5, 2),
            "share":      float(row["share"]),
            "mom_imp":    pct_ch(float(row["impressions"]), float(prev["imp"])) if prev else None,
            "mom_share":  pp_ch(float(row["share"]), float(prev["share"])) if prev else None,
        })

    all_months = sorted(kw["month"].unique())[-12:]
    all_cats = kw["category"].unique().tolist()
    cat_matrix = []
    for cat in all_cats:
        row = {"category": cat}
        for m in all_months:
            v = kw[(kw["month"]==m) & (kw["category"]==cat)]["impressions"].sum()
            row[m] = int(v) if v > 0 else 0
        cat_matrix.append(row)

    return {"monthly": mon_rows, "categories": cat_rows, "cat_months": all_months, "cat_matrix": cat_matrix}

def build_gsc_country(key, csv_name, kw_prefix):
    monthly  = build_monthly_country(csv_name)
    daily    = build_gsc_daily_country(csv_name)
    weekly   = build_gsc_weekly_country(csv_name)
    keywords = build_keywords_country(kw_prefix)
    extras   = build_country_extras(key)
    print(f"  ✓ GSC [{key}]: {len(monthly)} months | {len(daily)} days | {len(weekly)} weeks | "
          f"keywords: {len(keywords['monthly'])} months, {len(keywords['categories'])} categories")
    return {
        "monthly_impressions": monthly, "gsc_daily": daily, "gsc_weekly": weekly, "keywords": keywords,
        "bsos": extras["bsos"], "gindex": extras["gindex"],
    }

def build_city_tiers():
    p = DATA / "city_tiers.csv"
    if not p.exists():
        print("  ⚠ city_tiers.csv missing (city tiers will be empty)")
        return {}
    df = pd.read_csv(p)
    return dict(zip(df["city"], df["tier"]))

# ── Keywords ──────────────────────────────────────────────────────────────────
def build_keywords():
    files = sorted(DATA.glob("20*.csv"))
    if not files:
        print("  ⚠ No keyword CSVs found"); return {"monthly": [], "categories": []}
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            if "impressions" in df.columns and "category" in df.columns:
                month = f.stem  # e.g. "2026-05"
                df["month"] = month
                dfs.append(df[["keyword","category","impressions","month"]])
        except Exception as e:
            print(f"  ⚠ Skipping {f.name}: {e}")
    if not dfs:
        return {"monthly": [], "categories": []}
    kw = pd.concat(dfs, ignore_index=True)
    kw["impressions"] = pd.to_numeric(kw["impressions"], errors="coerce").fillna(0)

    # Monthly totals
    mon = kw.groupby("month")["impressions"].sum().reset_index().sort_values("month").reset_index(drop=True)
    mon_rows = []
    for i, row in mon.iterrows():
        pr = mon.iloc[i-1] if i > 0 else None
        yoy_m = str(pd.Period(row["month"], freq="M") - 12)
        yoy_r = mon[mon["month"] == yoy_m]
        yoy_v = float(yoy_r["impressions"].iloc[0]) if not yoy_r.empty else None
        mon_rows.append({
            "month": row["month"],
            "label": mlabel(row["month"]),
            "impressions": int(row["impressions"]),
            "imp_lakh": round(float(row["impressions"]) / 1e5, 2),
            "mom": pct_ch(float(row["impressions"]), float(pr["impressions"]) if pr is not None else None),
            "yoy": pct_ch(float(row["impressions"]), yoy_v),
        })

    # Category breakdown for latest month
    latest_m = mon["month"].max()
    cat_df = kw[kw["month"] == latest_m].groupby("category")["impressions"].sum().reset_index()
    total_cat = cat_df["impressions"].sum()
    cat_df["share"] = (cat_df["impressions"] / total_cat * 100).round(1)
    cat_df = cat_df.sort_values("impressions", ascending=False)
    # Previous month for MoM
    prev_m_cats = sorted(kw["month"].unique())
    prev_m_cats = [m for m in prev_m_cats if m < latest_m]
    prev_m = prev_m_cats[-1] if prev_m_cats else None
    cat_prev = {}
    if prev_m:
        cp = kw[kw["month"] == prev_m].groupby("category")["impressions"].sum().to_dict()
        prev_total = sum(cp.values())
        cat_prev = {k: {"imp": v, "share": v/prev_total*100 if prev_total else 0} for k,v in cp.items()}

    cat_rows = []
    for _, row in cat_df.iterrows():
        cat = row["category"]
        prev = cat_prev.get(cat, {})
        cat_rows.append({
            "category":   cat,
            "impressions": int(row["impressions"]),
            "imp_lakh":   round(float(row["impressions"])/1e5, 2),
            "share":      float(row["share"]),
            "mom_imp":    pct_ch(float(row["impressions"]), float(prev["imp"])) if prev else None,
            "mom_share":  pp_ch(float(row["share"]), float(prev["share"])) if prev else None,
        })

    # Category × month matrix (last 12 months)
    all_months = sorted(kw["month"].unique())[-12:]
    all_cats = kw["category"].unique().tolist()
    cat_matrix = []
    for cat in all_cats:
        row = {"category": cat}
        for m in all_months:
            v = kw[(kw["month"]==m) & (kw["category"]==cat)]["impressions"].sum()
            row[m] = int(v) if v > 0 else 0
        cat_matrix.append(row)

    print(f"  ✓ Keywords: {len(mon_rows)} months, {len(cat_rows)} categories")
    return {
        "monthly": mon_rows,
        "categories": cat_rows,
        "cat_months": all_months,
        "cat_matrix": cat_matrix,
    }

# ── KPIs ──────────────────────────────────────────────────────────────────────
def build_kpis(monthly, bsos_monthly):
    if not monthly: return {}
    lat = monthly[-1]
    brands = ["Cars24","Spinny","CarWale","Cardekho","MFC","MTV","OLX"]
    brand_sos = {}
    c24_sos = c24_sos_mom = spinny_sos = carwale_sos = None
    c24_rank = None

    if bsos_monthly:
        bm = bsos_monthly[-1]
        bmp = bsos_monthly[-2] if len(bsos_monthly) >= 2 else None
        for b in brands:
            if b in bm and bm[b] is not None:
                brand_sos[b] = bm[b]
        c24_sos = brand_sos.get("Cars24")
        spinny_sos = brand_sos.get("Spinny")
        carwale_sos = brand_sos.get("CarWale")
        if c24_sos is not None and bmp:
            c24_sos_mom = pp_ch(c24_sos, sf(bmp.get("Cars24")))
        ranked = sorted(brand_sos.items(), key=lambda x: x[1], reverse=True)
        for rk, (b,_) in enumerate(ranked, 1):
            if b == "Cars24": c24_rank = rk; break

    peak = max(monthly, key=lambda r: r["impressions"])
    sos_ratio = (c24_sos / spinny_sos * 100) if (c24_sos and spinny_sos and spinny_sos > 0) else None

    return {
        "latest_month":       lat["month"],
        "latest_month_label": lat["label"],
        "curr_imp":           lat["impressions"],
        "curr_imp_lakh":      lat["imp_lakh"],
        "curr_imp_fmt":       fmt_lakh(lat["impressions"]),
        "mom_imp":            lat.get("mom"),
        "yoy_imp":            lat.get("yoy"),
        "is_ath":             lat["impressions"] == peak["impressions"],
        "peak_month":         peak["month"],
        "peak_month_label":   peak["label"],
        "peak_imp_fmt":       fmt_lakh(peak["impressions"]),
        "c24_sos":            sf(c24_sos),
        "c24_sos_mom":        sf(c24_sos_mom),
        "spinny_sos":         sf(spinny_sos),
        "carwale_sos":        sf(carwale_sos),
        "sos_ratio":          sf(sos_ratio),
        "c24_rank":           c24_rank,
        "brand_sos":          {k: sf(v) for k,v in brand_sos.items()},
        "c24_vs_spinny":      sf(pp_ch(c24_sos, spinny_sos)),
        "c24_vs_carwale":     sf(pp_ch(c24_sos, carwale_sos)),
    }

# ── Influencers ───────────────────────────────────────────────────────────────
INFLUENCER_URL = "https://cars24-influencer-dashboard.pages.dev/live_data.json"

def build_influencers():
    """Fetch live influencer data from the Cars24 influencer dashboard."""
    raw = None
    # Try requests first (better SSL handling), fall back to urllib with certifi
    try:
        import requests
        resp = requests.get(INFLUENCER_URL, timeout=20, headers={"User-Agent": "Cars24-Dashboard/1.0"})
        resp.raise_for_status()
        raw = resp.json()
    except ImportError:
        pass
    except Exception as e:
        print(f"  ⚠ Influencer fetch (requests) failed: {e}")

    if raw is None:
        import urllib.request, ssl
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        try:
            req = urllib.request.Request(INFLUENCER_URL, headers={"User-Agent": "Cars24-Dashboard/1.0"})
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                raw = json.loads(resp.read())
        except Exception as e:
            print(f"  ⚠ Influencer fetch failed: {e}"); return {}

    rows = raw.get("rows", [])
    if not rows:
        print("  ⚠ Influencer dashboard: 0 rows"); return {}

    # Platform detection from link URL
    for r in rows:
        lnk = (r.get("link") or "") + (r.get("videoLink") or "")
        if "instagram.com" in lnk:
            r["platform"] = "Instagram"
        elif "youtube.com" in lnk or "youtu.be" in lnk:
            r["platform"] = "YouTube"
        else:
            r["platform"] = "Other"

    # Summary KPIs
    total_views = sum(r.get("views") or 0 for r in rows)
    total_cost  = sum(r.get("cost")  or 0 for r in rows)
    valid_cpv   = [r["cpv"]     for r in rows if r.get("cpv")     and r["cpv"] > 0]
    valid_eng   = [r["engRate"] for r in rows if r.get("engRate") and r["engRate"] > 0]

    # Monthly aggregates
    from collections import defaultdict
    monthly = defaultdict(lambda: {"views":0,"cost":0,"campaigns":0,"cpvs":[],"engs":[]})
    for r in rows:
        key = (r.get("liveMonth","Unknown"), r.get("monthOrder", 999999))
        monthly[key]["views"]     += r.get("views") or 0
        monthly[key]["cost"]      += r.get("cost")  or 0
        monthly[key]["campaigns"] += 1
        if r.get("cpv"):     monthly[key]["cpvs"].append(r["cpv"])
        if r.get("engRate"): monthly[key]["engs"].append(r["engRate"])

    monthly_rows = []
    for (m, mo), v in sorted(monthly.items(), key=lambda x: x[0][1]):
        monthly_rows.append({
            "month":      m,
            "monthOrder": mo,
            "campaigns":  v["campaigns"],
            "views":      v["views"],
            "views_lakh": round(v["views"] / 1e5, 2),
            "cost":       v["cost"],
            "avg_cpv":    round(sum(v["cpvs"]) / len(v["cpvs"]), 3) if v["cpvs"] else None,
            "avg_eng":    round(sum(v["engs"]) / len(v["engs"]), 2) if v["engs"] else None,
        })

    print(f"  ✓ Influencers: {len(rows)} campaigns · {len(monthly_rows)} months")
    return {
        "kpis": {
            "total_campaigns":  len(rows),
            "total_views":      total_views,
            "total_views_lakh": round(total_views / 1e5, 2),
            "total_cost":       total_cost,
            "avg_cpv":          round(sum(valid_cpv)/len(valid_cpv), 3) if valid_cpv else None,
            "avg_eng":          round(sum(valid_eng)/len(valid_eng), 2) if valid_eng else None,
        },
        "monthly":      monthly_rows,
        "rows":         rows,
        "refreshed_at": raw.get("refreshedAt", ""),
    }

# ── YouTube ───────────────────────────────────────────────────────────────────
YT_CHANNEL_KEYS = [
    "cars24_india", "teambhp", "cars24_insider", "cars24_malayalam",
    "cars24_tamil", "cars24_au", "cars24_uae",
]
YT_CHANNEL_NAMES = {
    "cars24_india":      "Cars24 India",
    "teambhp":           "TeamBHP",
    "cars24_insider":    "Cars24 Insider",
    "cars24_malayalam":  "Cars24 Malayalam",
    "cars24_tamil":      "Cars24 Tamil",
    "cars24_au":         "Cars24 Australia",
    "cars24_uae":        "Cars24 UAE",
}

def build_youtube():
    result = {}
    for key in YT_CHANNEL_KEYS:
        p = DATA / f"youtube_{key}.csv"
        if not p.exists():
            continue
        try:
            df = pd.read_csv(p)
            if df.empty:
                continue
            df = df.sort_values("month").reset_index(drop=True)

            snap = {}
            if "total_subscribers" in df.columns:
                snap["subscribers"] = int(df["total_subscribers"].iloc[-1])
            if "total_views" in df.columns:
                snap["total_views"] = int(df["total_views"].iloc[-1])
            if "total_videos" in df.columns:
                snap["videos"] = int(df["total_videos"].iloc[-1])

            # Load extra JSON if available
            extra_path = DATA / f"youtube_{key}_extra.json"
            extra = {}
            if extra_path.exists():
                try:
                    with open(extra_path) as ef:
                        extra = json.load(ef)
                except Exception as e:
                    print(f"  ⚠ YouTube {key} extra.json: {e}")

            rows = []
            for i, row in df.iterrows():
                views = int(row.get("views", 0))
                wt    = sf(row.get("watch_time_hours"))
                subs  = int(row.get("subscribers_gained", 0))
                likes    = int(row.get("likes", 0))
                comments = int(row.get("comments", 0))
                shares   = int(row.get("shares", 0))
                avg_dur  = sf(row.get("avg_view_duration"))

                # avg_view_percent from CSV column if present
                avg_view_pct = 0
                if "avg_view_percent" in df.columns:
                    v = sf(row.get("avg_view_percent"))
                    if v is not None:
                        avg_view_pct = v

                # MoM calculations
                mom_views = None
                mom_wt    = None
                mom_subs  = None
                if i > 0:
                    prev = df.iloc[i - 1]
                    pv = int(prev.get("views", 0))
                    pw = sf(prev.get("watch_time_hours"))
                    ps = int(prev.get("subscribers_gained", 0))
                    if pv:
                        mom_views = round((views - pv) / pv * 100, 1)
                    if pw and pw != 0 and wt is not None:
                        mom_wt = round((wt - pw) / abs(pw) * 100, 1)
                    if ps:
                        mom_subs = round((subs - ps) / ps * 100, 1)

                # YoY calculations (same month 12 rows back)
                yoy_views = None
                yoy_wt    = None
                yoy_subs  = None
                if i >= 12:
                    yoy_row = df.iloc[i - 12]
                    yv = int(yoy_row.get("views", 0))
                    yw = sf(yoy_row.get("watch_time_hours"))
                    ys = int(yoy_row.get("subscribers_gained", 0))
                    if yv:
                        yoy_views = round((views - yv) / yv * 100, 1)
                    if yw and yw != 0 and wt is not None:
                        yoy_wt = round((wt - yw) / abs(yw) * 100, 1)
                    if ys:
                        yoy_subs = round((subs - ys) / ys * 100, 1)

                # Engagement rate = (likes + subs gained + shares + comments) / views
                engagement_rate = round((likes + subs + comments + shares) / views * 100, 2) if views > 0 else 0

                # avg_view_duration in minutes
                avg_view_duration_min = round(avg_dur / 60, 1) if avg_dur is not None else None

                r = {
                    "month":                str(row["month"])[:7],
                    "label":                mlabel(str(row["month"])[:7]),
                    "views":                views,
                    "watch_time_hours":     wt,
                    "avg_view_duration":    avg_dur,
                    "avg_view_duration_min": avg_view_duration_min,
                    "avg_view_percent":     avg_view_pct,
                    "subscribers_gained":   subs,
                    "subscribers_lost":     int(row.get("subscribers_lost", 0)),
                    "net_subs":             int(row.get("net_subs", 0)),
                    "likes":                likes,
                    "comments":             comments,
                    "shares":               shares,
                    "impressions":          int(row.get("impressions", 0)),
                    "ctr":                  sf(row.get("ctr")),
                    "videos_published":         int(row.get("videos_published", 0)),
                    "videos_published_shorts":  int(row.get("videos_published_shorts", 0)),
                    "videos_published_long":    int(row.get("videos_published_long", 0)),
                    "data_source":          str(row.get("data_source", "analytics")),
                    "mom_views":            mom_views,
                    "mom_wt":               mom_wt,
                    "mom_subs":             mom_subs,
                    "yoy_views":            yoy_views,
                    "yoy_wt":               yoy_wt,
                    "yoy_subs":             yoy_subs,
                    "engagement_rate":      engagement_rate,
                }
                rows.append(r)

            result[key] = {
                "channel_name":  YT_CHANNEL_NAMES.get(key, key),
                "snapshot":      snap,
                "monthly":       rows,
                "geo":           extra.get("geo", []),
                "demographics":  extra.get("demographics", []),
                "traffic_sources": extra.get("traffic_sources", []),
                "devices":       extra.get("devices", []),
                "geo_monthly":           extra.get("geo_monthly", {}),
                "demographics_monthly":  extra.get("demographics_monthly", {}),
                "traffic_sources_monthly": extra.get("traffic_sources_monthly", {}),
                "devices_monthly":       extra.get("devices_monthly", {}),
                "top_videos":    extra.get("top_videos", []),
            }
            print(f"  ✓ YouTube {key}: {len(rows)} months | geo:{len(extra.get('geo',[]))} | demo:{len(extra.get('demographics',[]))} | traffic:{len(extra.get('traffic_sources',[]))} | devices:{len(extra.get('devices',[]))}")
        except Exception as e:
            print(f"  ⚠ YouTube {key}: {e}")
    return result

# ── Instagram ─────────────────────────────────────────────────────────────────
IG_KEYS = ["cars24_india", "teambhp", "cars24_au", "cars24_uae"]
IG_HANDLES = {
    "cars24_india": "@cars24india",
    "teambhp":      "@teambhp",
    "cars24_au":    "@cars24australia",
    "cars24_uae":   "@cars24uae",
}

def build_instagram():
    result = {}
    for key in IG_KEYS:
        p  = DATA / f"instagram_{key}.csv"
        pp = DATA / f"instagram_{key}_posts.csv"
        if not p.exists() and not pp.exists():
            continue
        try:
            # Account-level only: followers + the two metrics with no per-post
            # equivalent (profile_views, accounts_engaged).
            acct_by_month = {}
            snap = {}
            if p.exists():
                df = pd.read_csv(p)
                if not df.empty:
                    df = df.sort_values("month").reset_index(drop=True)
                    if "total_followers" in df.columns:
                        snap["followers"] = int(df["total_followers"].iloc[-1])
                    if "total_media" in df.columns:
                        snap["media"] = int(df["total_media"].iloc[-1])
                    for _, row in df.iterrows():
                        acct_by_month[str(row["month"])[:7]] = {
                            "followers":        int(row.get("followers", 0)),
                            "followers_gained": int(row.get("followers_gained", 0)),
                            "followers_lost":   int(row.get("followers_lost", 0)),
                            "net_followers":    int(row.get("net_followers", 0)),
                            "profile_views":    int(row.get("profile_views", 0)),
                            "accounts_engaged": int(row.get("accounts_engaged", 0)),
                        }

            # Posts — full history. Views/reach/likes/comments/shares/content_posted
            # are computed by summing every post published in a given month (same
            # "sum the live content" pattern as the Influencer dashboard) rather than
            # trusting Instagram's account-level Insights, which blend organic and
            # paid/boosted delivery with no way to split them.
            posts = []
            from collections import defaultdict
            monthly_from_posts = defaultdict(lambda: {
                "views": 0, "reach": 0, "likes": 0, "comments": 0,
                "shares": 0, "saves": 0, "interactions": 0, "content_posted": 0,
            })
            if pp.exists():
                pdf = pd.read_csv(pp)
                for _, pr in pdf.iterrows():
                    d = str(pr.get("date", ""))[:10]
                    post = {
                        "date":         d,
                        "type":         str(pr.get("type", "")),
                        "caption":      str(pr.get("caption", ""))[:100],
                        "url":          str(pr.get("url", "")),
                        "likes":        int(pr.get("likes", 0)),
                        "comments":     int(pr.get("comments", 0)),
                        "views":        int(pr.get("views", 0)),
                        "reach":        int(pr.get("reach", 0)),
                        "saves":        int(pr.get("saves", 0)),
                        "shares":       int(pr.get("shares", 0)),
                        "interactions": int(pr.get("interactions", 0)),
                    }
                    posts.append(post)
                    if d[:7]:
                        agg = monthly_from_posts[d[:7]]
                        agg["views"]          += post["views"]
                        agg["reach"]          += post["reach"]
                        agg["likes"]          += post["likes"]
                        agg["comments"]       += post["comments"]
                        agg["shares"]         += post["shares"]
                        agg["saves"]          += post["saves"]
                        agg["interactions"]   += post["interactions"]
                        agg["content_posted"] += 1

            months = sorted(set(acct_by_month) | set(monthly_from_posts))
            rows = []
            for m in months:
                a = acct_by_month.get(m, {})
                c = monthly_from_posts.get(m, {})
                views    = c.get("views", 0)
                likes    = c.get("likes", 0)
                comments = c.get("comments", 0)
                shares   = c.get("shares", 0)
                saves    = c.get("saves", 0)
                engagement_rate = round((likes + comments + shares + saves) / views * 100, 2) if views > 0 else 0
                rows.append({
                    "month":              m,
                    "label":              mlabel(m),
                    "followers":          a.get("followers", 0),
                    "followers_gained":   a.get("followers_gained", 0),
                    "followers_lost":     a.get("followers_lost", 0),
                    "net_followers":      a.get("net_followers", 0),
                    "views":              views,
                    "reach":              c.get("reach", 0),
                    "profile_views":      a.get("profile_views", 0),
                    "accounts_engaged":   a.get("accounts_engaged", 0),
                    "total_interactions": c.get("interactions", 0),
                    "likes":              likes,
                    "comments":           comments,
                    "shares":             shares,
                    "saves":              saves,
                    "content_posted":     c.get("content_posted", 0),
                    "engagement_rate":    engagement_rate,
                })

            # Drop leading months with no views data. Instagram only started
            # exposing the unified "views" insight metric in 2023 — older posts
            # predate it, so early months show views=0 not because there was no
            # activity but because the metric didn't exist yet. Trim the series to
            # start from the first month it actually has views, rather than padding
            # every chart/KPI total with a long flat run of misleading zeros.
            first_views_idx = next((i for i, r in enumerate(rows) if r["views"] > 0), None)
            if first_views_idx:
                rows = rows[first_views_idx:]

            # Follower demographics — current-month snapshot only (IG Insights has no
            # historical time series for this), age/gender/city/country breakdowns
            demographics = {}
            dp = DATA / f"instagram_{key}_extra.json"
            if dp.exists():
                try:
                    with open(dp) as df_:
                        demographics = json.load(df_)
                except Exception:
                    pass

            result[key] = {
                "handle":       IG_HANDLES.get(key, key),
                "snapshot":     snap,
                "monthly":      rows,
                "posts":        posts,
                "demographics": demographics,
            }
            print(f"  ✓ Instagram {key}: {len(rows)} months, {len(posts)} posts")
        except Exception as e:
            print(f"  ⚠ Instagram {key}: {e}")
    return result

# ── LinkedIn ──────────────────────────────────────────────────────────────────
# Expected files in data/:
#   linkedin_cars24_followers.csv   — from LinkedIn Page → Analytics → Followers → Export
#   linkedin_cars24_content.csv     — from LinkedIn Page → Analytics → Content → Export
#   linkedin_cars24_visitors.csv    — from LinkedIn Page → Analytics → Visitors → Export
#   (same pattern for linkedin_careers_*.csv)
#
# LinkedIn export column names vary by locale — we normalise below.

LI_PAGES = {
    "cars24":         "Cars24 India",
    "cars24_arabia":  "Cars24 Arabia",
    "cars24_au":      "Cars24 Australia",
}

# LinkedIn's "Followers" export is a daily GAINS report (new followers per day), not a
# running total — so the CSV's "Total followers" column has to be reconstructed into a
# cumulative trend by anchoring to a known current total and walking backwards day by day.
# {page_key: (known_total, "YYYY-MM-DD" the total was true as of)}
LI_KNOWN_TOTAL_FOLLOWERS = {
    "cars24": (464286, "2026-07-03"),
}

def _li_col(df, *candidates):
    """Return first matching column name (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        hit = cols_lower.get(cand.lower())
        if hit:
            return hit
    return None

def _li_int(row, *cols):
    for c in cols:
        v = row.get(c)
        if v is not None and str(v).strip() not in ("", "—", "-", "nan"):
            try: return int(float(str(v).replace(",", "")))
            except: pass
    return 0

def _li_float(row, *cols):
    for c in cols:
        v = row.get(c)
        if v is not None and str(v).strip() not in ("", "—", "-", "nan"):
            try: return round(float(str(v).replace(",", "").replace("%", "")), 4)
            except: pass
    return None

# Follower/visitor demographic breakdowns — LinkedIn's own export is a current-
# snapshot CSV with no date column, so there's no historical time series built
# in. We build one ourselves by archiving one snapshot per calendar month as
# build_data.py runs (re-running within the same month overwrites that month's
# archive with the latest export rather than adding a duplicate entry), so a
# period filter becomes meaningful once a few months have accumulated.
LI_DEMO_DIMS = ["location", "job_function", "seniority", "industry", "company_size"]
LI_DEMO_SNAP_DIR = DATA / "li_demo_snapshots"

def _li_load_demo_csv(path):
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path)
        return [{"category": str(r["category"]), "value": int(r["value"])} for _, r in df.iterrows()]
    except Exception:
        return []

def _li_snapshot_demo(key, kind, dims_data, month):
    if not any(dims_data.values()):
        return
    LI_DEMO_SNAP_DIR.mkdir(exist_ok=True)
    path = LI_DEMO_SNAP_DIR / f"{key}_{kind}_{month}.json"
    with open(path, "w") as f:
        json.dump(dims_data, f)

def _li_load_demo_history(key, kind):
    """{month: {...dim: [...] for each LI_DEMO_DIMS}} for every archived snapshot,
    sorted ascending by month."""
    if not LI_DEMO_SNAP_DIR.exists():
        return {}
    history = {}
    prefix = f"{key}_{kind}_"
    for p in sorted(LI_DEMO_SNAP_DIR.glob(f"{prefix}*.json")):
        month = p.stem[len(prefix):]
        try:
            history[month] = json.loads(p.read_text())
        except Exception:
            continue
    return history

def build_linkedin_competitors():
    """Shared competitor snapshot (not per-page) — Cars24 vs other major brands on
    LinkedIn Page followers/engagement. Single point-in-time export, no history."""
    p = DATA / "linkedin_competitor_analytics.csv"
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p)
        df.columns = [c.strip() for c in df.columns]
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "page":          str(r.get("Page", "")),
                "followers":     _li_int(r, "Total Followers"),
                "new_followers": _li_int(r, "New Followers"),
                "engagements":   _li_int(r, "Total post engagements"),
                "posts":         _li_int(r, "Total posts"),
            })
        rows.sort(key=lambda x: x["followers"], reverse=True)
        print(f"  ✓ LinkedIn competitor analytics: {len(rows)} brands")
        return rows
    except Exception as e:
        print(f"  ⚠ LinkedIn competitor analytics: {e}")
        return []

def build_linkedin():
    result = {}
    for key, name in LI_PAGES.items():
        fol_p = DATA / f"linkedin_{key}_followers.csv"
        con_p = DATA / f"linkedin_{key}_content.csv"
        vis_p = DATA / f"linkedin_{key}_visitors.csv"

        if not fol_p.exists() and not con_p.exists():
            continue

        fol_demo = {dim: _li_load_demo_csv(DATA / f"linkedin_{key}_followers_by_{dim}.csv") for dim in LI_DEMO_DIMS}
        vis_demo = {dim: _li_load_demo_csv(DATA / f"linkedin_{key}_visitors_by_{dim}.csv")  for dim in LI_DEMO_DIMS}
        current_month = str(pd.Timestamp("today").to_period("M"))
        _li_snapshot_demo(key, "followers", fol_demo, current_month)
        _li_snapshot_demo(key, "visitors", vis_demo, current_month)
        fol_demo_history = _li_load_demo_history(key, "followers")
        vis_demo_history = _li_load_demo_history(key, "visitors")

        page_data = {
            "page_name": name, "snapshot": {}, "monthly": [], "posts": [],
            "follower_demographics": fol_demo,
            "visitor_demographics":  vis_demo,
            "follower_demographics_monthly": {m: {**d, "label": mlabel(m)} for m, d in fol_demo_history.items()},
            "visitor_demographics_monthly":  {m: {**d, "label": mlabel(m)} for m, d in vis_demo_history.items()},
        }

        # ── Followers CSV ──────────────────────────────────────────────────
        if fol_p.exists():
            try:
                df = pd.read_csv(fol_p, skiprows=2)  # LinkedIn exports have 2 header rows
                df.columns = [c.strip() for c in df.columns]
                date_col = _li_col(df, "date", "Date")
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df.dropna(subset=[date_col])
                    df = df.sort_values(date_col).reset_index(drop=True)
                    df["_month"] = df[date_col].dt.to_period("M").astype(str)

                    gain_col = _li_col(df, "total followers", "total_followers", "followers (total)",
                                        "new followers", "new_followers", "followers gained",
                                        "organic followers", "new organic followers")

                    if gain_col:
                        df["_gain"] = df[gain_col].fillna(0).astype(float)
                        # Reconstruct a cumulative running total: this CSV reports NEW
                        # followers gained per day, not a running total, so anchor the
                        # last day to a known real total and walk backwards.
                        known = LI_KNOWN_TOTAL_FOLLOWERS.get(key)
                        if known:
                            known_total, known_date = known
                            known_ts = pd.Timestamp(known_date)
                            gains_after = df.loc[df[date_col] > known_ts, "_gain"].sum()
                            running_end = known_total - gains_after
                        else:
                            running_end = int(df["_gain"].sum())
                        cum_gain = df["_gain"].cumsum()
                        df["_running_total"] = running_end - (cum_gain.iloc[-1] - cum_gain)
                        page_data["snapshot"]["followers"] = int(round(df["_running_total"].iloc[-1]))
                    else:
                        df["_running_total"] = 0

                    monthly_fol = df.groupby("_month").agg(
                        total_followers=("_running_total", "last"),
                        new_followers=("_gain", "sum") if gain_col else ("_month", "count"),
                    ).reset_index()

                    for _, row in monthly_fol.iterrows():
                        page_data["monthly"].append({
                            "month": str(row["_month"]),
                            "label": mlabel(str(row["_month"])),
                            "followers": _li_int(row, "total_followers"),
                            "new_followers": _li_int(row, "new_followers"),
                        })
                print(f"  ✓ LinkedIn {key} followers: {len(page_data['monthly'])} months")
            except Exception as e:
                print(f"  ⚠ LinkedIn {key} followers: {e}")

        # ── Visitors CSV ───────────────────────────────────────────────────
        if vis_p.exists():
            try:
                df = pd.read_csv(vis_p, skiprows=2)
                df.columns = [c.strip() for c in df.columns]
                date_col = _li_col(df, "date", "Date")
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df.dropna(subset=[date_col])
                    df["_month"] = df[date_col].dt.to_period("M").astype(str)

                    pv_col  = _li_col(df, "total page views", "page views (total)", "desktop page views",
                                       "total page views (total)", "overview page views (total)")
                    uv_col  = _li_col(df, "unique visitors", "desktop unique visitors",
                                       "total unique visitors (total)", "overview unique visitors (total)")

                    monthly_vis = df.groupby("_month").agg(
                        page_views=(pv_col, "sum") if pv_col else ("_month", "count"),
                        unique_visitors=(uv_col, "sum") if uv_col else ("_month", "count"),
                    ).reset_index()

                    # Merge into existing monthly rows
                    vis_map = {str(r["_month"]): r for _, r in monthly_vis.iterrows()}
                    for m in page_data["monthly"]:
                        v = vis_map.get(m["month"], {})
                        m["page_views"]      = _li_int(v, "page_views")
                        m["unique_visitors"]  = _li_int(v, "unique_visitors")
                print(f"  ✓ LinkedIn {key} visitors merged")
            except Exception as e:
                print(f"  ⚠ LinkedIn {key} visitors: {e}")

        # ── Content / Posts CSV ────────────────────────────────────────────
        if con_p.exists():
            try:
                df = pd.read_csv(con_p, skiprows=2)
                df.columns = [c.strip() for c in df.columns]
                date_col = _li_col(df, "published date", "created date", "date")
                imp_col  = _li_col(df, "impressions", "Impressions")
                clk_col  = _li_col(df, "clicks", "Clicks")
                lk_col   = _li_col(df, "likes", "Likes", "reactions")
                cmt_col  = _li_col(df, "comments", "Comments")
                shr_col  = _li_col(df, "shares", "Shares", "reposts")
                eng_col  = _li_col(df, "engagement rate", "engagement rate (organic)")
                ttl_col  = _li_col(df, "content title", "post", "title", "update", "post title")

                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df.dropna(subset=[date_col])
                    df["_month"] = df[date_col].dt.to_period("M").astype(str)

                    # Monthly content aggregates
                    agg = {"posts": ("_month", "count")}
                    if imp_col: agg["impressions"] = (imp_col, "sum")
                    if clk_col: agg["clicks"]      = (clk_col, "sum")
                    if lk_col:  agg["likes"]       = (lk_col,  "sum")
                    if cmt_col: agg["comments"]    = (cmt_col, "sum")
                    if shr_col: agg["shares"]      = (shr_col, "sum")

                    monthly_con = df.groupby("_month").agg(**agg).reset_index()
                    con_map = {str(r["_month"]): r for _, r in monthly_con.iterrows()}
                    for m in page_data["monthly"]:
                        v = con_map.get(m["month"], {})
                        m["posts"]       = _li_int(v, "posts")
                        m["impressions"] = _li_int(v, "impressions")
                        m["clicks"]      = _li_int(v, "clicks")
                        m["likes"]       = _li_int(v, "likes")
                        m["comments"]    = _li_int(v, "comments")
                        m["shares"]      = _li_int(v, "shares")
                        total_eng = m["likes"] + m["comments"] + m["shares"] + m["clicks"]
                        m["eng_rate"]    = round(total_eng / m["impressions"] * 100, 2) if m["impressions"] else None

                    # Top posts
                    post_rows = []
                    for _, row in df.sort_values(imp_col or "_month", ascending=False).head(50).iterrows():
                        post_rows.append({
                            "date":        str(row[date_col])[:10],
                            "month":       str(row["_month"]),
                            "title":       str(row[ttl_col])[:120] if ttl_col else "—",
                            "impressions": _li_int(row, imp_col) if imp_col else 0,
                            "clicks":      _li_int(row, clk_col) if clk_col else 0,
                            "likes":       _li_int(row, lk_col)  if lk_col  else 0,
                            "comments":    _li_int(row, cmt_col) if cmt_col else 0,
                            "shares":      _li_int(row, shr_col) if shr_col else 0,
                            "eng_rate":    _li_float(row, eng_col) if eng_col else None,
                        })
                    page_data["posts"] = post_rows

                    # Snapshot
                    if imp_col:
                        page_data["snapshot"]["total_impressions"] = int(df[imp_col].sum())
                print(f"  ✓ LinkedIn {key} content: {len(post_rows)} posts")
            except Exception as e:
                print(f"  ⚠ LinkedIn {key} content: {e}")

        if page_data["monthly"] or page_data["posts"]:
            page_data["monthly"].sort(key=lambda x: x["month"])
            result[key] = page_data

    return result

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Building data.json …")
    monthly        = build_monthly()
    bsos_monthly   = build_bsos_monthly()
    bsos_weekly    = build_bsos_weekly()
    bsos_daily     = build_bsos_daily()
    bsos_cities    = build_bsos_cities()
    gsc_daily      = build_gsc_daily()
    gsc_weekly     = build_gsc_weekly()
    print(f"  GSC weekly: {len(gsc_weekly)} weeks")
    gindex         = build_gindex()
    city_tiers     = build_city_tiers()
    keywords       = build_keywords()
    kpis           = build_kpis(monthly, bsos_monthly)
    youtube        = build_youtube()
    instagram      = build_instagram()
    influencers    = build_influencers()
    linkedin       = build_linkedin()
    linkedin_competitors = build_linkedin_competitors()
    gsc_au         = build_gsc_country("au", "gsc_daily_au.csv", "au_")
    gsc_uae        = build_gsc_country("uae", "gsc_daily_uae.csv", "uae_")

    payload = {
        "_meta": {
            "built":               datetime.now().strftime("%Y-%m-%d %H:%M"),
            "latest_month":        kpis.get("latest_month",""),
            "latest_month_label":  kpis.get("latest_month_label",""),
        },
        "kpis":               kpis,
        "monthly_impressions": monthly,
        "bsos_monthly":       bsos_monthly,
        "bsos_weekly":        bsos_weekly,
        "bsos_daily":         bsos_daily,
        "bsos_cities":        bsos_cities,
        "gsc_daily":          gsc_daily,
        "gsc_weekly":         gsc_weekly,
        "google_index":       gindex,
        "city_tiers":         city_tiers,
        "keywords":           keywords,
        "youtube":            youtube,
        "instagram":          instagram,
        "influencers":        influencers,
        "linkedin":           linkedin,
        "linkedin_competitors": linkedin_competitors,
        "gsc_au":             gsc_au,
        "gsc_uae":            gsc_uae,
    }

    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    sz = OUT.stat().st_size / 1024
    print(f"\n✅ data.json written — {sz:.0f} KB")
    print(f"   Impressions: {len(monthly)} months | BSOS: {len(bsos_monthly)} months | Cities: {len(bsos_cities)}")
    print(f"   YouTube: {len(youtube)} channels | Instagram: {len(instagram)} accounts | LinkedIn: {len(linkedin)} pages")
    inf_count = influencers.get("kpis", {}).get("total_campaigns", 0)
    print(f"   Influencers: {inf_count} campaigns")
    print(f"   KPIs: {kpis.get('curr_imp_fmt')} impressions · {kpis.get('c24_sos')}% SoS")
