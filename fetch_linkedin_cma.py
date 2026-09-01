#!/usr/bin/env python3
"""
LinkedIn Community Management API (/rest, version 202508) fetcher for the
Cars24 brand dashboard — replaces the retired /v2 Marketing-API parsing that
returned all-zeros.

For each Page (Cars24 India / Arabia / Australia) it writes:
  • linkedin_<key>_followers_by_{location,job_function,seniority,industry,
    company_size}.csv   — follower demographics  (category,value)
  • linkedin_<key>_visitors_by_{...}.csv          — visitor demographics
And one shared file:
  • linkedin_totals.json  — {key: {total_followers, total_views, content:{...}}}
    (read by build_data.py for the snapshot + content-overview KPIs)

It does NOT touch linkedin_<key>_content.csv / _followers.csv / _visitors.csv,
which hold the individual-post / daily-trend exports.

URN → label resolution:
  • seniority / function : paginated list endpoints (cached in-process)
  • industry / geo       : BATCH id→name lookups (?ids=List(...)), persisted to
    data/linkedin_label_cache.json so the nightly cron re-resolves nothing.

Requires LI_ACCESS_TOKEN in .env (from setup_linkedin_auth.py). Read-only.
"""
import csv
import json
import os
import time
from pathlib import Path

import requests

DATA = Path("data")
REST = "https://api.linkedin.com/rest"
# LinkedIn retires dated API versions ~yearly. This is a sensible default;
# _resolve_version() auto-detects the newest active one at runtime so the fetch
# self-heals when a version ages out (as 202401 → 202508 → 202608 have).
LI_VERSION = "202608"

LI_PAGES = {
    "cars24":        "10429660",   # Cars24 India
    "cars24_arabia": "81800309",   # Cars24 Arabia
    "cars24_au":     "73063943",   # Cars24 Australia
}

STAFF_LABELS = {
    "SIZE_1": "1", "SIZE_2_TO_10": "2-10", "SIZE_11_TO_50": "11-50",
    "SIZE_51_TO_200": "51-200", "SIZE_201_TO_500": "201-500",
    "SIZE_501_TO_1000": "501-1000", "SIZE_1001_TO_5000": "1001-5000",
    "SIZE_5001_TO_10000": "5001-10000", "SIZE_10001_OR_MORE": "10001+",
}
_LABEL_ENDPOINT = {"seniority": "seniorities", "function": "functions"}

_cache = {"seniority": None, "function": None, "industry": {}, "geo": {}}
_LABEL_CACHE_FILE = DATA / "linkedin_label_cache.json"


# ── HTTP ──────────────────────────────────────────────────────────────────────
def _headers():
    return {
        "Authorization": f"Bearer {os.environ['LI_ACCESS_TOKEN']}",
        "LinkedIn-Version": LI_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _resolve_version():
    """Pick the newest active LinkedIn API version (they retire dated versions
    ~yearly). Probe from the current month backwards; set LI_VERSION to the first
    that responds 200, so the fetch keeps working after a version ages out."""
    global LI_VERSION
    import datetime
    today = datetime.date.today()
    y, m = today.year, today.month
    for _ in range(15):
        ver = f"{y}{m:02d}"
        try:
            r = requests.get(f"{REST}/seniorities",
                             headers={"Authorization": f"Bearer {os.environ['LI_ACCESS_TOKEN']}",
                                      "LinkedIn-Version": ver, "X-Restli-Protocol-Version": "2.0.0"},
                             params={"count": 1}, timeout=15)
            if r.status_code == 200:
                LI_VERSION = ver
                return ver
        except requests.RequestException:
            pass
        m -= 1
        if m == 0:
            m = 12; y -= 1
    return LI_VERSION


def _get(path, params=None, retries=5):
    last = None
    for i in range(retries):
        try:
            r = requests.get(f"{REST}{path}", params=params or {}, headers=_headers(), timeout=30)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:150]}"
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 * (i + 1)); continue
            raise RuntimeError(last)
        except requests.RequestException as e:
            last = str(e)[:120]
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed after {retries} tries: {path} ({last})")


# ── Label resolution ──────────────────────────────────────────────────────────
def _load_label_cache():
    if _LABEL_CACHE_FILE.exists():
        try:
            saved = json.loads(_LABEL_CACHE_FILE.read_text())
            _cache["industry"].update(saved.get("industry", {}))
            _cache["geo"].update(saved.get("geo", {}))
        except Exception:
            pass


def _save_label_cache():
    try:
        _LABEL_CACHE_FILE.write_text(json.dumps(
            {"industry": _cache["industry"], "geo": _cache["geo"]}, indent=0, sort_keys=True))
    except Exception:
        pass


def _paginated_labels(kind):
    """{id: name} for seniorities / functions (small paginated lists)."""
    if _cache[kind] is not None:
        return _cache[kind]
    out, start, endpoint = {}, 0, _LABEL_ENDPOINT[kind]
    try:
        while start <= 500:
            d = _get(f"/{endpoint}", {"start": start, "count": 50})
            for el in d.get("elements", []):
                nm = el.get("name", {}).get("localized", {}).get("en_US")
                if el.get("id") is not None and nm:
                    out[str(el["id"])] = nm
            pg = d.get("paging", {})
            if not d.get("elements") or start + pg.get("count", 0) >= pg.get("total", len(out)):
                break
            start += 50
    except Exception:
        # throttled/unavailable — return whatever resolved; don't crash the fetch
        # (the demographic guard keeps existing good CSVs rather than degrading them)
        return out
    _cache[kind] = out
    return out


def _one_name(kind, d):
    return (d.get("name", {}).get("localized", {}).get("en_US")
            or d.get("defaultLocalizedName", {}).get("value"))


def _batch_resolve(kind, ids):
    """Resolve uncached industry/geo ids: batched first, then single-get any the
    batch missed (batch can silently drop ids). Never caches a fallback, so a
    transient miss is retried next run instead of being frozen in the cache."""
    endpoint = "industries" if kind == "industry" else "geo"
    todo = sorted({str(i) for i in ids if str(i) and str(i) not in _cache[kind]})
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        try:
            d = _get(f"/{endpoint}", {"ids": "List(" + ",".join(chunk) + ")"})
            for k, v in (d.get("results") or {}).items():
                nm = _one_name(kind, v)
                if nm:
                    _cache[kind][str(k)] = nm
        except Exception:
            pass
    # single-get whatever the batch didn't resolve (reliable, and rare once cached)
    for i in todo:
        if i not in _cache[kind]:
            try:
                nm = _one_name(kind, _get(f"/{endpoint}/{i}"))
                if nm:
                    _cache[kind][i] = nm
            except Exception:
                pass


def _urn_id(v):
    return str(v).split(":")[-1] if v is not None else ""


# ── CSV writing ───────────────────────────────────────────────────────────────
def _write_demo(key, aud, dim, rows):
    rows = [(str(c), int(v)) for c, v in rows if v]
    if not rows:
        return
    # Anti-regression: industry/location labels come from URN lookups that can be
    # rate-limited; an unresolved label shows as a bare numeric id. If too many
    # are unresolved, keep the existing (good-label) CSV instead of overwriting it.
    if dim in ("industry", "location", "seniority", "job_function"):
        unresolved = sum(1 for c, _ in rows if c.strip().isdigit())
        if unresolved > len(rows) * 0.25:
            print(f"    ⚠ {key} {aud} {dim}: {unresolved}/{len(rows)} labels unresolved — keeping existing CSV")
            return
    rows.sort(key=lambda x: x[1], reverse=True)
    with open(DATA / f"linkedin_{key}_{aud}_by_{dim}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["category", "value"]); w.writerows(rows)


# ── Core ──────────────────────────────────────────────────────────────────────
def _follower_count(fc):
    return (fc.get("organicFollowerCount", 0) or 0) + (fc.get("paidFollowerCount", 0) or 0)


def _seg_views(seg):
    return seg.get("pageStatistics", {}).get("views", {}).get("allPageViews", {}).get("pageViews", 0) or 0


def _write_follower_demo(key, fs, sen, fun):
    def coll(api_key, field, lab):
        return [(lab(x.get(field)), _follower_count(x.get("followerCounts", {}))) for x in fs.get(api_key, [])]
    _write_demo(key, "followers", "seniority",
                coll("followerCountsBySeniority", "seniority", lambda u: sen.get(_urn_id(u), _urn_id(u))))
    _write_demo(key, "followers", "job_function",
                coll("followerCountsByFunction", "function", lambda u: fun.get(_urn_id(u), _urn_id(u))))
    _write_demo(key, "followers", "industry",
                coll("followerCountsByIndustry", "industry", lambda u: _cache["industry"].get(_urn_id(u), _urn_id(u))))
    _write_demo(key, "followers", "company_size",
                coll("followerCountsByStaffCountRange", "staffCountRange", lambda u: STAFF_LABELS.get(str(u), str(u))))
    _write_demo(key, "followers", "location",
                coll("followerCountsByGeo", "geo", lambda u: _cache["geo"].get(_urn_id(u), _urn_id(u))))
    return sum(_follower_count(x.get("followerCounts", {})) for x in fs.get("followerCountsByGeoCountry", []))


def _write_visitor_demo(key, ps, sen, fun):
    def coll(api_key, field, lab):
        return [(lab(x.get(field)), _seg_views(x)) for x in ps.get(api_key, [])]
    _write_demo(key, "visitors", "seniority",
                coll("pageStatisticsBySeniority", "seniority", lambda u: sen.get(_urn_id(u), _urn_id(u))))
    _write_demo(key, "visitors", "job_function",
                coll("pageStatisticsByFunction", "function", lambda u: fun.get(_urn_id(u), _urn_id(u))))
    _write_demo(key, "visitors", "industry",
                coll("pageStatisticsByIndustryV2", "industryV2", lambda u: _cache["industry"].get(_urn_id(u), _urn_id(u))))
    _write_demo(key, "visitors", "company_size",
                coll("pageStatisticsByStaffCountRange", "staffCountRange", lambda u: STAFF_LABELS.get(str(u), str(u))))
    _write_demo(key, "visitors", "location",
                coll("pageStatisticsByGeo", "geo", lambda u: _cache["geo"].get(_urn_id(u), _urn_id(u))))
    tv = ps.get("totalPageStatistics", {}).get("views", {})
    return (tv.get("allDesktopPageViews", {}).get("pageViews", 0) or 0) + \
           (tv.get("allMobilePageViews", {}).get("pageViews", 0) or 0)


def main():
    from dotenv import load_dotenv
    load_dotenv(".env")
    if not os.environ.get("LI_ACCESS_TOKEN"):
        print("  ! LI_ACCESS_TOKEN not set — run setup_linkedin_auth.py"); return {}
    DATA.mkdir(exist_ok=True)
    _load_label_cache()
    ver = _resolve_version()
    print(f"── LinkedIn (Community Management API /rest {ver}) ──")

    # Pass 1 — pull raw stats for every org (2 stat calls each), collect URN ids.
    raw, ind_ids, geo_ids = {}, set(), set()
    for key, oid in LI_PAGES.items():
        urn = f"urn:li:organization:{oid}"
        try:
            fs = (_get("/organizationalEntityFollowerStatistics",
                       {"q": "organizationalEntity", "organizationalEntity": urn}).get("elements") or [{}])[0]
            ps = (_get("/organizationPageStatistics",
                       {"q": "organization", "organization": urn}).get("elements") or [{}])[0]
            ss = (_get("/organizationalEntityShareStatistics",
                       {"q": "organizationalEntity", "organizationalEntity": urn}).get("elements") or [{}])[0]
            raw[key] = (fs, ps, ss)
        except Exception as e:
            print(f"    ✗ {key}: {e}"); continue
        for x in fs.get("followerCountsByIndustry", []): ind_ids.add(_urn_id(x.get("industry")))
        for x in ps.get("pageStatisticsByIndustryV2", []): ind_ids.add(_urn_id(x.get("industryV2")))
        for x in fs.get("followerCountsByGeo", []): geo_ids.add(_urn_id(x.get("geo")))
        for x in ps.get("pageStatisticsByGeo", []): geo_ids.add(_urn_id(x.get("geo")))

    # Resolve all labels (batched industry/geo + paginated seniority/function).
    _batch_resolve("industry", ind_ids)
    _batch_resolve("geo", geo_ids)
    sen, fun = _paginated_labels("seniority"), _paginated_labels("function")
    _save_label_cache()

    # Pass 2 — write demographics + collect totals.
    totals = {}
    for key, (fs, ps, ss) in raw.items():
        tf = _write_follower_demo(key, fs, sen, fun)
        tv = _write_visitor_demo(key, ps, sen, fun)
        s = ss.get("totalShareStatistics", {})
        totals[key] = {
            "total_followers": tf,
            "total_views": tv,
            "content": {
                "impressions": s.get("impressionCount", 0),
                "unique_impressions": s.get("uniqueImpressionsCount", 0),
                "clicks": s.get("clickCount", 0),
                "likes": s.get("likeCount", 0),
                "comments": s.get("commentCount", 0),
                "shares": s.get("shareCount", 0),
                "engagement_rate": round(s.get("engagement", 0) or 0, 4),
            },
        }
        print(f"    {key}: {tf:,} followers · {tv:,} page views · {s.get('impressionCount', 0):,} impressions")

    if totals:
        (DATA / "linkedin_totals.json").write_text(json.dumps(totals, indent=1))
    return totals


if __name__ == "__main__":
    main()
