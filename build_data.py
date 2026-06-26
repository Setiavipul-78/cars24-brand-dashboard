#!/usr/bin/env python3
"""
Build data.json for the Cars24 static HTML dashboard.
Run: python3 build_data.py
"""

import json, math, sys
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
            df["ws"] = df["date"].dt.to_period("W").apply(lambda x: x.start_time)
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
        monthly = grp.groupby("month")[bc].mean().reset_index().sort_values("month").reset_index(drop=True)
        city_rows = []
        for i, row in monthly.iterrows():
            pr = monthly.iloc[i-1] if i > 0 else None
            r = {"month": row["month"], "label": mlabel(row["month"])}
            for b in bc:
                v = sf(row.get(b))
                r[b] = v
                r[f"{b}_mom"] = pp_ch(v, sf(pr.get(b)) if pr is not None else None)
            city_rows.append(r)
        result[city] = city_rows
    print(f"  ✓ City BSOS: {len(result)} cities")
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
    rows = rows[-90:]
    print(f"  ✓ GSC daily: {len(rows)} days")
    return rows

# ── Google Indexed ────────────────────────────────────────────────────────────
def build_google_indexed():
    p = DATA / "bsos_google_monthly.csv"
    if not p.exists():
        print("  ⚠ bsos_google_monthly.csv missing (Tab 4 will be empty)"); return []
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
    print(f"  ✓ Google Indexed: {len(rows)} months")
    return rows

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

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Building data.json …")
    monthly        = build_monthly()
    bsos_monthly   = build_bsos_monthly()
    bsos_weekly    = build_bsos_weekly()
    bsos_daily     = build_bsos_daily()
    bsos_cities    = build_bsos_cities()
    gsc_daily      = build_gsc_daily()
    google_indexed = build_google_indexed()
    keywords       = build_keywords()
    kpis           = build_kpis(monthly, bsos_monthly)

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
        "google_indexed":     google_indexed,
        "keywords":           keywords,
    }

    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    sz = OUT.stat().st_size / 1024
    print(f"\n✅ data.json written — {sz:.0f} KB")
    print(f"   Impressions: {len(monthly)} months | BSOS: {len(bsos_monthly)} months | Cities: {len(bsos_cities)}")
    print(f"   KPIs: {kpis.get('curr_imp_fmt')} impressions · {kpis.get('c24_sos')}% SoS")
