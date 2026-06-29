#!/usr/bin/env python3
"""
Fetch live social media metrics for Cars24 brand dashboard.

Pulls from:
  • YouTube Analytics API v2  — views, subscribers, watch time, CTR (monthly)
  • Instagram Graph API       — followers, reach, impressions, profile views (monthly)
  • LinkedIn API              — followers (basic, no partner required)
                               impressions/content (requires LinkedIn Marketing Partner)

Output CSVs in data/:
  youtube_cars24_india.csv, youtube_teambhp.csv, youtube_cars24_insider.csv
  youtube_cars24_au.csv, youtube_cars24_uae.csv
  instagram_cars24_india.csv, instagram_teambhp.csv
  instagram_cars24_au.csv, instagram_cars24_uae.csv
  linkedin_cars24_followers.csv, linkedin_cars24_visitors.csv, linkedin_cars24_content.csv

Usage:
  1. Complete setup once:  python3 setup_youtube_auth.py
  2. Fill .env with Instagram credentials (see .env.example)
  3. For LinkedIn: python3 setup_linkedin_auth.py  (then add LI_ORG_ID_CARS24 to .env)
  4. Run:  python3 fetch_social.py
  5. Then: python3 build_data.py
"""

import os, csv, json, time, sys
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
DATA = Path("data")
DATA.mkdir(exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def mlabel(m: str) -> str:
    try:
        return datetime.strptime(m, "%Y-%m").strftime("%b'%y")
    except Exception:
        return m

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        print(f"  ⚠  no rows for {path.name}"); return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f"  ✓  {path.name}  ({len(rows)} rows)")

# ── YouTube Analytics API ─────────────────────────────────────────────────────
YT_CHANNELS = {
    "cars24_india":     os.getenv("YT_CHANNEL_ID_CARS24_INDIA"),
    "teambhp":          os.getenv("YT_CHANNEL_ID_TEAMBHP"),
    "cars24_insider":   os.getenv("YT_CHANNEL_ID_INSIDER"),
    "cars24_malayalam": os.getenv("YT_CHANNEL_ID_CARS24_MALAYALAM"),
    "cars24_au":        os.getenv("YT_CHANNEL_ID_AU"),
    "cars24_uae":       os.getenv("YT_CHANNEL_ID_UAE"),
}

# Per-channel token env var overrides (key → env var name for refresh token)
YT_TOKEN_KEYS = {
    "cars24_uae":      "YT_REFRESH_TOKEN_UAE",
    "cars24_india":    "YT_REFRESH_TOKEN_INDIA",
    "teambhp":         "YT_REFRESH_TOKEN_TEAMBHP",
    "cars24_insider":  "YT_REFRESH_TOKEN_INSIDER",
    "cars24_malayalam":"YT_REFRESH_TOKEN_MALAYALAM",
}

def get_yt_credentials(channel_key: str = None):
    """Build OAuth2 credentials from stored refresh token.
    Uses per-channel token if available (YT_REFRESH_TOKEN_<KEY>), else falls back to default."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        print("  ! Run: pip install google-api-python-client google-auth-oauthlib")
        return None

    token_env = YT_TOKEN_KEYS.get(channel_key, "YT_REFRESH_TOKEN") if channel_key else "YT_REFRESH_TOKEN"
    refresh_token = os.getenv(token_env)
    if not refresh_token:
        print(f"  ! No refresh token for {channel_key} (expected env var: {token_env})")
        print(f"    Run: python3 setup_youtube_auth.py --account {channel_key.replace('cars24_', '')}")
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/yt-analytics.readonly",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
    )
    for attempt in range(3):
        try:
            creds.refresh(Request())
            return creds
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            print(f"  ! OAuth refresh failed for {channel_key}: {e}")
            print(f"    Run: python3 setup_youtube_auth.py --account {(channel_key or '').replace('cars24_', '')}")
            return None

def _yt_row_template(m, total_subs, total_views, total_videos):
    return {
        "month": m, "label": mlabel(m),
        "views": 0, "watch_time_hours": 0, "avg_view_duration": 0,
        "subscribers_gained": 0, "subscribers_lost": 0, "net_subs": 0,
        "likes": 0, "comments": 0, "shares": 0,
        "impressions": 0, "ctr": 0, "videos_published": 0,
        "data_source": "analytics",
        "total_subscribers": total_subs, "total_views": total_views, "total_videos": total_videos,
    }

def fetch_yt_channel_analytics(key: str, channel_id: str, creds) -> list[dict]:
    """Pull monthly analytics (requires channel owner OAuth)."""
    from googleapiclient.discovery import build
    yta = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    ytd = build("youtube", "v3", credentials=creds, cache_discovery=False)

    snap = ytd.channels().list(part="statistics", id=channel_id).execute()
    stats = snap["items"][0]["statistics"] if snap.get("items") else {}
    total_subs   = int(stats.get("subscriberCount", 0))
    total_views  = int(stats.get("viewCount", 0))
    total_videos = int(stats.get("videoCount", 0))

    start = datetime(datetime.today().year - 2, 1, 1).strftime("%Y-%m-%d")
    today = date.today()
    end   = today.replace(day=1).strftime("%Y-%m-%d")

    # Monthly metrics including averageViewPercentage
    resp  = yta.reports().query(
        ids=f"channel=={channel_id}", startDate=start, endDate=end,
        dimensions="month",
        metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares",
        sort="month",
    ).execute()

    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = []
    for r in resp.get("rows", []):
        row = dict(zip(headers, r))
        m = row.get("month", "")[:7]
        sg = int(row.get("subscribersGained", 0))
        sl = int(row.get("subscribersLost", 0))
        base = _yt_row_template(m, total_subs, total_views, total_videos)
        base.update({
            "views":              int(row.get("views", 0)),
            "watch_time_hours":   round(float(row.get("estimatedMinutesWatched", 0)) / 60, 1),
            "avg_view_duration":  round(float(row.get("averageViewDuration", 0)), 0),
            "avg_view_percent":   round(float(row.get("averageViewPercentage", 0)), 2),
            "subscribers_gained": sg,
            "subscribers_lost":   sl,
            "net_subs":           sg - sl,
            "likes":              int(row.get("likes", 0)),
            "comments":           int(row.get("comments", 0)),
            "shares":             int(row.get("shares", 0)),
        })
        rows.append(base)

    # Build month-indexed dict for impressions/CTR merge
    rows_by_month = {r["month"]: r for r in rows}

    # Fetch daily impressions + CTR, then aggregate by month
    try:
        daily_resp = yta.reports().query(
            ids=f"channel=={channel_id}", startDate=start, endDate=end,
            dimensions="day",
            metrics="impressions,impressionsClickThroughRate",
            sort="day",
        ).execute()
        daily_headers = [h["name"] for h in daily_resp.get("columnHeaders", [])]
        from collections import defaultdict
        imp_by_month = defaultdict(lambda: {"impressions": 0, "ctr_sum": 0.0, "ctr_count": 0})
        for dr in daily_resp.get("rows", []):
            drow = dict(zip(daily_headers, dr))
            dm = drow.get("day", "")[:7]
            imp_by_month[dm]["impressions"] += int(drow.get("impressions", 0))
            ctr_val = float(drow.get("impressionsClickThroughRate", 0))
            imp_by_month[dm]["ctr_sum"] += ctr_val
            imp_by_month[dm]["ctr_count"] += 1
        # Merge impressions and avg CTR into monthly rows
        for m, agg in imp_by_month.items():
            if m in rows_by_month:
                rows_by_month[m]["impressions"] = agg["impressions"]
                rows_by_month[m]["ctr"] = round(agg["ctr_sum"] / agg["ctr_count"], 4) if agg["ctr_count"] else 0
    except Exception as e:
        print(f"    ⚠  Daily impressions/CTR fetch failed for {key}: {e}")

    # Fetch extra dimension data and save to JSON
    extra = {}

    # Geo: top cities
    try:
        geo_resp = yta.reports().query(
            ids=f"channel=={channel_id}", startDate=start, endDate=end,
            dimensions="city",
            metrics="views,estimatedMinutesWatched",
            sort="-views",
            maxResults=25,
        ).execute()
        geo_headers = [h["name"] for h in geo_resp.get("columnHeaders", [])]
        geo_rows = []
        for gr in geo_resp.get("rows", []):
            grow = dict(zip(geo_headers, gr))
            geo_rows.append({
                "city":             grow.get("city", ""),
                "views":            int(grow.get("views", 0)),
                "watch_time_hours": round(float(grow.get("estimatedMinutesWatched", 0)) / 60, 1),
            })
        extra["geo"] = geo_rows
        print(f"    geo: {len(geo_rows)} cities")
    except Exception as e:
        print(f"    ⚠  Geo fetch failed for {key}: {e}")

    # Demographics: age group + gender
    try:
        demo_resp = yta.reports().query(
            ids=f"channel=={channel_id}", startDate=start, endDate=end,
            dimensions="ageGroup,gender",
            metrics="viewerPercentage",
        ).execute()
        demo_headers = [h["name"] for h in demo_resp.get("columnHeaders", [])]
        demo_rows = []
        for dr in demo_resp.get("rows", []):
            drow = dict(zip(demo_headers, dr))
            demo_rows.append({
                "age_group":    drow.get("ageGroup", ""),
                "gender":       drow.get("gender", ""),
                "viewer_pct":   round(float(drow.get("viewerPercentage", 0)), 2),
            })
        extra["demographics"] = demo_rows
        print(f"    demographics: {len(demo_rows)} segments")
    except Exception as e:
        print(f"    ⚠  Demographics fetch failed for {key}: {e}")

    # Traffic sources
    try:
        traffic_resp = yta.reports().query(
            ids=f"channel=={channel_id}", startDate=start, endDate=end,
            dimensions="insightTrafficSourceType",
            metrics="views,estimatedMinutesWatched",
            sort="-views",
        ).execute()
        traffic_headers = [h["name"] for h in traffic_resp.get("columnHeaders", [])]
        traffic_raw = []
        for tr in traffic_resp.get("rows", []):
            trow = dict(zip(traffic_headers, tr))
            traffic_raw.append({
                "source":           trow.get("insightTrafficSourceType", ""),
                "views":            int(trow.get("views", 0)),
                "watch_time_hours": round(float(trow.get("estimatedMinutesWatched", 0)) / 60, 1),
            })
        total_views_traffic = sum(r["views"] for r in traffic_raw) or 1
        for r in traffic_raw:
            r["pct"] = round(r["views"] / total_views_traffic * 100, 1)
        extra["traffic_sources"] = traffic_raw
        print(f"    traffic_sources: {len(traffic_raw)} sources")
    except Exception as e:
        print(f"    ⚠  Traffic sources fetch failed for {key}: {e}")

    # Devices
    try:
        device_resp = yta.reports().query(
            ids=f"channel=={channel_id}", startDate=start, endDate=end,
            dimensions="deviceType",
            metrics="views,estimatedMinutesWatched",
            sort="-views",
        ).execute()
        device_headers = [h["name"] for h in device_resp.get("columnHeaders", [])]
        device_raw = []
        for dr in device_resp.get("rows", []):
            drow = dict(zip(device_headers, dr))
            device_raw.append({
                "device":           drow.get("deviceType", ""),
                "views":            int(drow.get("views", 0)),
                "watch_time_hours": round(float(drow.get("estimatedMinutesWatched", 0)) / 60, 1),
            })
        total_views_device = sum(r["views"] for r in device_raw) or 1
        for r in device_raw:
            r["pct"] = round(r["views"] / total_views_device * 100, 1)
        extra["devices"] = device_raw
        print(f"    devices: {len(device_raw)} types")
    except Exception as e:
        print(f"    ⚠  Devices fetch failed for {key}: {e}")

    # Top videos (per-video analytics + metadata)
    try:
        vid_resp = yta.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start, endDate=today.strftime("%Y-%m-%d"),
            dimensions="video",
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,comments,shares",
            sort="-views", maxResults=50,
        ).execute()
        vid_headers = [h["name"] for h in vid_resp.get("columnHeaders", [])]
        vid_rows = vid_resp.get("rows", [])
        vid_ids = [r[0] for r in vid_rows]
        meta = {}
        if vid_ids:
            meta_resp = ytd.videos().list(
                part="snippet,contentDetails", id=",".join(vid_ids[:50])
            ).execute()
            meta = {v["id"]: v for v in meta_resp.get("items", [])}
        videos = []
        for r in vid_rows:
            row = dict(zip(vid_headers, r))
            vid_id = row.get("video", "")
            m = meta.get(vid_id, {})
            snippet = m.get("snippet", {})
            views = int(row.get("views", 0))
            likes = int(row.get("likes", 0))
            comments = int(row.get("comments", 0))
            shares = int(row.get("shares", 0))
            videos.append({
                "id":              vid_id,
                "title":           snippet.get("title", vid_id),
                "published":       snippet.get("publishedAt", "")[:10],
                "url":             f"https://www.youtube.com/watch?v={vid_id}",
                "thumbnail":       snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
                "views":           views,
                "watch_time_hours": round(float(row.get("estimatedMinutesWatched", 0)) / 60, 2),
                "avg_duration_sec": round(float(row.get("averageViewDuration", 0)), 0),
                "avg_view_pct":    round(float(row.get("averageViewPercentage", 0)), 1),
                "subs_gained":     int(row.get("subscribersGained", 0)),
                "likes":           likes,
                "comments":        comments,
                "shares":          shares,
                "engagement_rate": round((likes + comments + shares) / views * 100, 2) if views else 0,
            })
        extra["top_videos"] = videos
        print(f"    top_videos: {len(videos)} videos")
    except Exception as e:
        print(f"    ⚠  Top videos fetch failed for {key}: {e}")

    # Save extra data to JSON
    extra_path = DATA / f"youtube_{key}_extra.json"
    with open(extra_path, "w") as f:
        json.dump(extra, f, indent=2)
    print(f"    ✓  {extra_path.name}")

    return rows

def fetch_yt_channel_public(key: str, channel_id: str, creds) -> list[dict]:
    """
    Pull public channel stats + video list via YouTube Data API v3.
    Works with manager/editor access — no analytics API needed.
    Views = current cumulative views per video, grouped by publish month.
    """
    from googleapiclient.discovery import build
    from collections import defaultdict

    ytd = build("youtube", "v3", credentials=creds, cache_discovery=False)

    snap = ytd.channels().list(part="statistics", id=channel_id).execute()
    if not snap.get("items"):
        print(f"    ! Channel {channel_id} not found")
        return []
    stats = snap["items"][0]["statistics"]
    total_subs   = int(stats.get("subscriberCount", 0))
    total_views  = int(stats.get("viewCount", 0))
    total_videos = int(stats.get("videoCount", 0))

    # Collect videos (up to 10 pages = 500 videos)
    monthly = defaultdict(lambda: {"views": 0, "likes": 0, "comments": 0, "count": 0})
    next_page = None
    for _ in range(10):
        params = {"part": "id", "channelId": channel_id, "type": "video",
                  "order": "date", "maxResults": 50}
        if next_page:
            params["pageToken"] = next_page
        search_resp = ytd.search().list(**params).execute()
        vid_ids = [item["id"]["videoId"] for item in search_resp.get("items", []) if item.get("id", {}).get("videoId")]
        if vid_ids:
            vstats = ytd.videos().list(part="statistics,snippet", id=",".join(vid_ids)).execute()
            for v in vstats.get("items", []):
                pub = v["snippet"]["publishedAt"][:7]
                vs  = v.get("statistics", {})
                monthly[pub]["views"]    += int(vs.get("viewCount", 0))
                monthly[pub]["likes"]    += int(vs.get("likeCount", 0))
                monthly[pub]["comments"] += int(vs.get("commentCount", 0))
                monthly[pub]["count"]    += 1
        next_page = search_resp.get("nextPageToken")
        if not next_page:
            break
        time.sleep(0.3)

    rows = []
    for m in sorted(monthly):
        d = monthly[m]
        base = _yt_row_template(m, total_subs, total_views, total_videos)
        base.update({
            "views":            d["views"],
            "likes":            d["likes"],
            "comments":         d["comments"],
            "videos_published": d["count"],
            "data_source":      "public",  # views = cumulative per-video, not monthly traffic
        })
        rows.append(base)
    return rows

def fetch_yt_channel(key: str, channel_id: str, creds) -> list[dict]:
    """Try analytics API first; fall back to public Data API v3 on 403."""
    if not channel_id:
        print(f"  ! No channel ID for {key}")
        return []
    try:
        rows = fetch_yt_channel_analytics(key, channel_id, creds)
        print(f"    analytics OK ({len(rows)} months)")
        return rows
    except Exception as e:
        if "403" in str(e) or "forbidden" in str(e).lower():
            print(f"    analytics 403 — falling back to public Data API")
            try:
                rows = fetch_yt_channel_public(key, channel_id, creds)
                print(f"    public data OK ({len(rows)} months of video history)")
                return rows
            except Exception as e2:
                print(f"    public data also failed: {e2}")
                return []
        raise

def fetch_all_youtube():
    print("\n── YouTube ──────────────────────────────────────────")
    if not any(YT_CHANNELS.values()):
        print("  ! No YT_CHANNEL_ID_* vars set in .env — skipping YouTube")
        return

    # Cache credentials per token env var to avoid redundant refreshes
    creds_cache = {}

    def get_creds_for(key):
        token_env = YT_TOKEN_KEYS.get(key, "YT_REFRESH_TOKEN")
        if token_env not in creds_cache:
            creds_cache[token_env] = get_yt_credentials(key)
        return creds_cache[token_env]

    for key, channel_id in YT_CHANNELS.items():
        if not channel_id:
            continue
        print(f"  Fetching {key}…")
        creds = get_creds_for(key)
        if not creds:
            print(f"  ↳ skipping {key} (no valid credentials)")
            continue
        try:
            rows = fetch_yt_channel(key, channel_id, creds)
            write_csv(DATA / f"youtube_{key}.csv", rows)
        except Exception as e:
            print(f"  ✗ {key}: {e}")
        time.sleep(0.5)

# ── Instagram Graph API ───────────────────────────────────────────────────────
IG_ACCOUNTS = {
    "cars24_india": {
        "user_id":      os.getenv("IG_USER_ID_CARS24_INDIA"),
        "access_token": os.getenv("IG_ACCESS_TOKEN_CARS24_INDIA") or os.getenv("IG_ACCESS_TOKEN"),
        "handle":       "@cars24india",
    },
    "teambhp": {
        "user_id":      os.getenv("IG_USER_ID_TEAMBHP"),
        "access_token": os.getenv("IG_ACCESS_TOKEN_TEAMBHP") or os.getenv("IG_ACCESS_TOKEN"),
        "handle":       "@teambhp",
    },
    "cars24_au": {
        "user_id":      os.getenv("IG_USER_ID_AU"),
        "access_token": os.getenv("IG_ACCESS_TOKEN_AU") or os.getenv("IG_ACCESS_TOKEN"),
        "handle":       "@cars24australia",
    },
    "cars24_uae": {
        "user_id":      os.getenv("IG_USER_ID_UAE"),
        "access_token": os.getenv("IG_ACCESS_TOKEN_UAE") or os.getenv("IG_ACCESS_TOKEN"),
        "handle":       "@cars24uae",
    },
}

BASE_IG = "https://graph.facebook.com/v19.0"

def ig_get(path: str, params: dict) -> dict:
    import requests
    r = requests.get(f"{BASE_IG}{path}", params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"IG API {r.status_code}: {r.text[:200]}")
    return r.json()

def fetch_ig_account(key: str, cfg: dict) -> list[dict]:
    """Pull monthly Instagram metrics for one account."""
    uid = cfg["user_id"]
    tok = cfg["access_token"]
    if not uid or not tok:
        print(f"  ! Skipping {key}: no IG_USER_ID / IG_ACCESS_TOKEN in .env")
        return []

    # Account snapshot
    snap = ig_get(f"/{uid}", {"fields": "followers_count,media_count,follows_count", "access_token": tok})
    total_followers = snap.get("followers_count", 0)
    total_media = snap.get("media_count", 0)

    # v21 IG Insights: all metrics use period=day + metric_type=total_value
    # Returns total_value.value for the queried window (max 30 days)
    # Use 28-day windows (1st to 29th) to stay within 30-day limit for all months
    ALL_METRICS = ["reach", "profile_views", "website_clicks",
                   "accounts_engaged", "total_interactions", "likes", "comments"]

    # Build months list — IG only keeps 2 years of data
    today = date.today()
    two_yrs_ago = date(today.year - 2, today.month + 1 if today.month < 12 else 1,
                       1 if today.month < 12 else 1)
    months = []
    yr, mo = today.year - 2, today.month + 1 if today.month < 12 else 1
    if today.month == 12:
        yr += 1
    # Simpler: just go from 24 months back
    yr, mo = today.year, today.month
    for _ in range(24):
        mo -= 1
        if mo == 0:
            mo = 12; yr -= 1
    start_yr, start_mo = yr, mo
    yr, mo = start_yr, start_mo
    while (yr, mo) <= (today.year, today.month):
        months.append(f"{yr:04d}-{mo:02d}")
        mo += 1
        if mo > 12:
            mo = 1; yr += 1

    rows = []
    for m in months:
        yr, mo = int(m[:4]), int(m[5:7])
        since_ts = int(datetime(yr, mo, 1).timestamp())
        # Use 28-day window to stay within IG's 30-day limit
        until_ts = since_ts + 28 * 86400

        met = {}
        try:
            d1 = ig_get(f"/{uid}/insights", {
                "metric": ",".join(ALL_METRICS), "period": "day",
                "metric_type": "total_value",
                "since": since_ts, "until": until_ts, "access_token": tok,
            })
            for item in d1.get("data", []):
                tv = item.get("total_value", {})
                met[item["name"]] = tv.get("value", 0) if isinstance(tv, dict) else 0
        except Exception as e:
            print(f"    ⚠  {m}: {str(e)[:80]}")
            continue

        # follower_count: use day period snapshot at end of window
        followers_eom = total_followers
        try:
            d3 = ig_get(f"/{uid}/insights", {
                "metric": "follower_count", "period": "day",
                "since": until_ts - 86400, "until": until_ts, "access_token": tok,
            })
            for item in d3.get("data", []):
                if item["name"] == "follower_count":
                    vals = item.get("values", [])
                    if vals:
                        followers_eom = vals[-1].get("value", total_followers)
        except Exception:
            pass

        rows.append({
            "month":              m,
            "label":              mlabel(m),
            "followers":          followers_eom,
            "reach":              met.get("reach", 0),
            "profile_views":      met.get("profile_views", 0),
            "website_clicks":     met.get("website_clicks", 0),
            "accounts_engaged":   met.get("accounts_engaged", 0),
            "total_interactions": met.get("total_interactions", 0),
            "likes":              met.get("likes", 0),
            "comments":           met.get("comments", 0),
            "total_followers":    total_followers,
            "total_media":        total_media,
        })
        time.sleep(0.3)

    return rows

def fetch_all_instagram():
    print("\n── Instagram ────────────────────────────────────────")
    try:
        import requests
    except ImportError:
        print("  ! Run: pip install requests")
        return

    for key, cfg in IG_ACCOUNTS.items():
        if not cfg["user_id"] or not cfg["access_token"]:
            continue
        print(f"  Fetching {cfg['handle']} ({key})…")
        try:
            rows = fetch_ig_account(key, cfg)
            write_csv(DATA / f"instagram_{key}.csv", rows)
        except Exception as e:
            print(f"  ✗ {key}: {e}")
        time.sleep(1)

# ── LinkedIn ──────────────────────────────────────────────────────────────────
# LinkedIn API tiers:
#   Basic (no approval) : GET /v2/organizations/{id}?fields=followersCount
#   Partner required    : followerStatistics, pageStatistics, shareStatistics
#
# Add to .env:
#   LI_ACCESS_TOKEN=AQxxxxxx          (from setup_linkedin_auth.py)
#   LI_ORG_ID_CARS24=1234567          (numeric org ID from LinkedIn Page URL)
#   LI_ORG_ID_CARS24_URN=urn:li:organization:1234567

LI_API = "https://api.linkedin.com/v2"

LI_ORGS = {
    "cars24": os.getenv("LI_ORG_ID_CARS24", ""),
}

def _li_headers():
    tok = os.getenv("LI_ACCESS_TOKEN", "")
    return {"Authorization": f"Bearer {tok}", "X-Restli-Protocol-Version": "2.0.0"}

def _li_get(path: str, params: dict = None):
    import requests as req
    r = req.get(f"{LI_API}{path}", headers=_li_headers(), params=params or {}, timeout=15)
    r.raise_for_status()
    return r.json()

def _li_time_range(months_back: int = 12):
    """Return LinkedIn API timeIntervals covering last N months (monthly granularity)."""
    from datetime import date, timedelta
    intervals = []
    today = date.today()
    for i in range(months_back, 0, -1):
        # First of month i months ago
        y = today.year - ((today.month - i - 1) // 12 + 1) if (today.month - i) <= 0 else today.year
        m = ((today.month - i - 1) % 12) + 1 if (today.month - i) <= 0 else today.month - i
        # simpler: use timedelta
        first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        # Just compute directly
        yr = today.year
        mo = today.month - i
        while mo <= 0:
            mo += 12; yr -= 1
        intervals.append({"start": {"year": yr, "month": mo, "day": 1}})
    return intervals

def fetch_li_org(key: str, org_id: str) -> dict:
    """
    Fetch what's available via LinkedIn API.
    Returns dict with keys: followers_rows, visitor_rows, content_rows
    All may be empty depending on API access level.
    """
    import requests as req
    results = {"followers_rows": [], "visitor_rows": [], "content_rows": []}
    urn = f"urn:li:organization:{org_id}"

    # ── 1. Basic follower count (no partner approval required) ─────────────
    try:
        org = _li_get(f"/organizations/{org_id}", {"fields": "localizedName,followersCount"})
        snap_followers = org.get("followersCount", 0)
        org_name = org.get("localizedName", key)
        print(f"    {org_name}: {snap_followers:,} followers (snapshot)")
    except Exception as e:
        print(f"    ! Basic org fetch failed: {e}")
        snap_followers = 0

    # ── 2. Follower statistics (requires r_organization_social / partner) ──
    try:
        stats = _li_get("/organizationFollowerStatistics", {
            "q":                "organizationalEntity",
            "organizationalEntity": urn,
        })
        elements = stats.get("elements", [])
        # Monthly rollup from lifetime stats
        if elements:
            el = elements[0]
            monthly_data = el.get("monthlyStatsByFunction", el.get("monthlyStats", []))
            for row in monthly_data:
                ti = row.get("timeRange", {})
                start = ti.get("start", {})
                mo_str = f"{start.get('year','')}-{str(start.get('month','')).zfill(2)}"
                gained = row.get("followerGains", {})
                results["followers_rows"].append({
                    "Date":            mo_str + "-01",
                    "Total Followers": snap_followers,  # API only gives delta; snapshot is latest
                    "New Followers":   gained.get("organicFollowerGain", 0) + gained.get("paidFollowerGain", 0),
                    "Organic Followers": gained.get("organicFollowerGain", 0),
                    "Paid Followers":  gained.get("paidFollowerGain", 0),
                })
            print(f"    Follower stats: {len(results['followers_rows'])} months (partner API)")
    except Exception as e:
        if "403" in str(e) or "MEMBER_NOT_AUTHORIZED" in str(e):
            print(f"    ! Follower statistics: requires LinkedIn Marketing Partner approval")
            # Fall back: write single snapshot row for today
            from datetime import date
            today = date.today()
            mo_str = f"{today.year}-{str(today.month).zfill(2)}-01"
            if snap_followers:
                results["followers_rows"] = [{"Date": mo_str, "Total Followers": snap_followers,
                                               "New Followers": "", "Organic Followers": "", "Paid Followers": ""}]
        else:
            print(f"    ! Follower stats error: {e}")

    # ── 3. Page / visitor statistics (requires partner) ────────────────────
    try:
        page_stats = _li_get("/organizationPageStatistics", {
            "q":                "organization",
            "organization":     urn,
            "timeIntervals.timeGranularityType": "MONTH",
        })
        for el in page_stats.get("elements", []):
            ti = el.get("timeRange", {})
            start = ti.get("start", {})
            mo_str = f"{start.get('year','')}-{str(start.get('month','')).zfill(2)}-01"
            views = el.get("totalPageStatistics", {}).get("views", {})
            results["visitor_rows"].append({
                "Date":                    mo_str,
                "Total Page Views":        views.get("allPageViews", {}).get("pageViews", 0),
                "Unique Visitors (total)": views.get("allPageViews", {}).get("uniquePageViews", 0),
            })
        print(f"    Page stats: {len(results['visitor_rows'])} months (partner API)")
    except Exception as e:
        if "403" in str(e) or "MEMBER_NOT_AUTHORIZED" in str(e):
            print(f"    ! Page statistics: requires LinkedIn Marketing Partner approval")
        else:
            print(f"    ! Page stats error: {e}")

    # ── 4. Share / content statistics (requires partner) ───────────────────
    try:
        share_stats = _li_get("/organizationalEntityShareStatistics", {
            "q":                "organizationalEntity",
            "organizationalEntity": urn,
            "timeIntervals.timeGranularityType": "MONTH",
        })
        for el in share_stats.get("elements", []):
            ti = el.get("timeRange", {})
            start = ti.get("start", {})
            mo_str = f"{start.get('year','')}-{str(start.get('month','')).zfill(2)}-01"
            s = el.get("totalShareStatistics", {})
            imps = s.get("impressionCount", 0)
            clks = s.get("clickCount", 0)
            lks  = s.get("likeCount", 0)
            cmts = s.get("commentCount", 0)
            shrs = s.get("shareCount", 0)
            results["content_rows"].append({
                "Published date": mo_str,
                "Content Title":  f"Monthly aggregate ({mo_str[:7]})",
                "Impressions":    imps,
                "Clicks":         clks,
                "Likes":          lks,
                "Comments":       cmts,
                "Shares":         shrs,
                "Engagement Rate": round((lks + cmts + shrs + clks) / imps, 4) if imps else "",
            })
        print(f"    Content stats: {len(results['content_rows'])} months (partner API)")
    except Exception as e:
        if "403" in str(e) or "MEMBER_NOT_AUTHORIZED" in str(e):
            print(f"    ! Content statistics: requires LinkedIn Marketing Partner approval")
        else:
            print(f"    ! Content stats error: {e}")

    return results

def fetch_all_linkedin():
    print("\n── LinkedIn ─────────────────────────────────────────")
    tok = os.getenv("LI_ACCESS_TOKEN", "")
    if not tok:
        print("  ! LI_ACCESS_TOKEN not set.")
        print("    Run: python3 setup_linkedin_auth.py")
        print("    Then add LI_ORG_ID_CARS24=<numeric-id> to .env")
        print("    (Find it in your LinkedIn Page URL: linkedin.com/company/<id>/admin)")
        return

    try:
        import requests
    except ImportError:
        print("  ! Run: pip install requests"); return

    for key, org_id in LI_ORGS.items():
        if not org_id:
            print(f"  ! LI_ORG_ID_{key.upper()} not set in .env")
            print(f"    Find your Page org ID in LinkedIn Page URL or run setup_linkedin_auth.py")
            continue

        print(f"  Fetching {key} (org {org_id})…")
        try:
            data = fetch_li_org(key, org_id)

            if data["followers_rows"]:
                write_csv(DATA / f"linkedin_{key}_followers.csv", data["followers_rows"])

            if data["visitor_rows"]:
                write_csv(DATA / f"linkedin_{key}_visitors.csv", data["visitor_rows"])

            if data["content_rows"]:
                write_csv(DATA / f"linkedin_{key}_content.csv", data["content_rows"])

            if not any(data.values()):
                print(f"  ! No data fetched for {key}. Check API access / org ID.")

        except Exception as e:
            print(f"  ✗ {key}: {e}")
        time.sleep(1)

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("═══ fetch_social.py ═══")
    fetch_all_youtube()
    fetch_all_instagram()
    fetch_all_linkedin()
    print("\n✅  Done — run: python3 build_data.py")
