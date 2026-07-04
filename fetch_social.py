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

import os, csv, json, time, sys, re
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
    "cars24_india":      os.getenv("YT_CHANNEL_ID_CARS24_INDIA"),
    "teambhp":           os.getenv("YT_CHANNEL_ID_TEAMBHP"),
    "cars24_insider":    os.getenv("YT_CHANNEL_ID_INSIDER"),
    "cars24_malayalam":  os.getenv("YT_CHANNEL_ID_CARS24_MALAYALAM"),   # Tamil
    "cars24_malayalam2": os.getenv("YT_CHANNEL_ID_CARS24_MALAYALAM2"),  # Malayalam
    "cars24_au":         os.getenv("YT_CHANNEL_ID_AU"),
    "cars24_uae":        os.getenv("YT_CHANNEL_ID_UAE"),
}

# Per-channel token env var overrides (key → env var name for refresh token)
YT_TOKEN_KEYS = {
    "cars24_uae":       "YT_REFRESH_TOKEN_UAE",
    "cars24_india":     "YT_REFRESH_TOKEN_INDIA",
    "teambhp":          "YT_REFRESH_TOKEN_TEAMBHP",
    "cars24_insider":   "YT_REFRESH_TOKEN_INSIDER",
    "cars24_malayalam": "YT_REFRESH_TOKEN_MALAYALAM",   # Tamil — vipul.setia@cars24.com
    "cars24_malayalam2":"YT_REFRESH_TOKEN_MALAYALAM2",  # Malayalam — vipul.setia@cars24.com
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
        "videos_published_shorts": 0, "videos_published_long": 0,
        "data_source": "analytics",
        "total_subscribers": total_subs, "total_views": total_views, "total_videos": total_videos,
    }

def _parse_iso8601_duration(s: str) -> int:
    """PT#H#M#S -> total seconds."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se

def fetch_video_publish_counts(channel_id: str, ytd) -> dict:
    """
    Cheap (1 quota unit/page) full listing of every video on the channel via its
    uploads playlist, classified Shorts (<=60s) vs long-form by duration.
    Returns {month: {"total": n, "shorts": n, "long_form": n}}.
    """
    from collections import defaultdict

    ch = ytd.channels().list(part="contentDetails", id=channel_id).execute()
    items = ch.get("items", [])
    if not items:
        return {}
    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_pubs = []  # [(video_id, publishedAt)]
    page_token = None
    for _ in range(40):  # up to 2000 videos
        resp = ytd.playlistItems().list(
            part="contentDetails", playlistId=uploads_id,
            maxResults=50, pageToken=page_token,
        ).execute()
        for it in resp.get("items", []):
            cd = it.get("contentDetails", {})
            vid = cd.get("videoId")
            pub = cd.get("videoPublishedAt")
            if vid and pub:
                video_pubs.append((vid, pub[:7]))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    monthly = defaultdict(lambda: {"total": 0, "shorts": 0, "long_form": 0})
    for i in range(0, len(video_pubs), 50):
        batch = video_pubs[i:i + 50]
        ids = ",".join(v[0] for v in batch)
        vresp = ytd.videos().list(part="contentDetails", id=ids).execute()
        dur_by_id = {v["id"]: _parse_iso8601_duration(v.get("contentDetails", {}).get("duration", "")) for v in vresp.get("items", [])}
        for vid, month in batch:
            dur = dur_by_id.get(vid, 0)
            bucket = monthly[month]
            bucket["total"] += 1
            if dur <= 60:
                bucket["shorts"] += 1
            else:
                bucket["long_form"] += 1
    return dict(monthly)

def fetch_yt_channel_analytics(key: str, channel_id: str, creds) -> list[dict]:
    """Pull monthly analytics (requires channel owner OAuth)."""
    from googleapiclient.discovery import build
    from collections import defaultdict
    yta = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    ytd = build("youtube", "v3", credentials=creds, cache_discovery=False)

    snap = ytd.channels().list(part="statistics", id=channel_id).execute()
    stats = snap["items"][0]["statistics"] if snap.get("items") else {}
    total_subs   = int(stats.get("subscriberCount", 0))
    total_views  = int(stats.get("viewCount", 0))
    total_videos = int(stats.get("videoCount", 0))

    start = datetime(datetime.today().year - 2, 1, 1).strftime("%Y-%m-%d")
    today = date.today()
    # Use first of NEXT month so current partial month is included
    _nm = today.replace(day=1)
    _nm = date(_nm.year + (_nm.month // 12), (_nm.month % 12) + 1, 1)
    end = _nm.strftime("%Y-%m-%d")

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

    # Build month-indexed dict for later merges (publish counts, traffic sources)
    rows_by_month = {r["month"]: r for r in rows}
    # NOTE: impressions/CTR are intentionally not fetched. As of early 2026 YouTube
    # retired `impressions`/`impressionsClickThroughRate` from the interactive Analytics
    # API; their successors (videoThumbnailImpressions / videoThumbnailImpressionsClickRate)
    # are recognized metric names but only queryable via the bulk YouTube Reporting API
    # (scheduled jobs + CSV download) — confirmed by direct API testing across every
    # dimension combination, not available through this synchronous reports().query() call.

    # Fetch full video list (cheap, 1 quota unit/page via uploads playlist) for
    # accurate per-month published counts, split Shorts (<=60s) vs long-form
    try:
        publish_counts = fetch_video_publish_counts(channel_id, ytd)
        for m, agg in publish_counts.items():
            if m in rows_by_month:
                rows_by_month[m]["videos_published"] = agg["total"]
                rows_by_month[m]["videos_published_shorts"] = agg["shorts"]
                rows_by_month[m]["videos_published_long"] = agg["long_form"]
    except Exception as e:
        print(f"    ⚠  Video publish-count fetch failed for {key}: {e}")

    # Fetch extra dimension data and save to JSON
    extra = {}

    # Geo: top cities (all-time only — confirmed via direct API testing that YouTube
    # Analytics API does not support combining `city` with any time dimension, day or month)
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

    # Demographics: age group + gender (all-time only — same API limitation as city;
    # ageGroup/gender cannot be combined with a time dimension)
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

    # Traffic sources (all-time snapshot + per-month breakdown, via day→month rollup —
    # confirmed `day,insightTrafficSourceType` IS a supported combination, unlike city/demo)
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
    try:
        traffic_m_resp = yta.reports().query(
            ids=f"channel=={channel_id}", startDate=start, endDate=end,
            dimensions="day,insightTrafficSourceType",
            metrics="views,estimatedMinutesWatched",
            sort="day",
            # No maxResults: with it set, the API silently truncates (confirmed via
            # testing — e.g. maxResults=4000 + sort=day kept only the OLDEST 9 months
            # and dropped everything since). Omitting it returns the full row set.
        ).execute()
        traffic_m_headers = [h["name"] for h in traffic_m_resp.get("columnHeaders", [])]
        traffic_by_month = defaultdict(lambda: defaultdict(lambda: {"views": 0, "watch_time_hours": 0.0}))
        for tr in traffic_m_resp.get("rows", []):
            trow = dict(zip(traffic_m_headers, tr))
            m = trow.get("day", "")[:7]
            src = trow.get("insightTrafficSourceType", "")
            bucket = traffic_by_month[m][src]
            bucket["views"] += int(trow.get("views", 0))
            bucket["watch_time_hours"] += round(float(trow.get("estimatedMinutesWatched", 0)) / 60, 1)
        for m, by_src in traffic_by_month.items():
            rows_m = [{"source": src, **agg} for src, agg in by_src.items()]
            tot = sum(r["views"] for r in rows_m) or 1
            for r in rows_m:
                r["pct"] = round(r["views"] / tot * 100, 1)
            traffic_by_month[m] = sorted(rows_m, key=lambda r: -r["views"])
        extra["traffic_sources_monthly"] = dict(traffic_by_month)
    except Exception as e:
        print(f"    ⚠  Traffic sources (monthly) fetch failed for {key}: {e}")

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
    try:
        device_m_resp = yta.reports().query(
            ids=f"channel=={channel_id}", startDate=start, endDate=end,
            dimensions="day,deviceType",
            metrics="views,estimatedMinutesWatched",
            sort="day",
            # No maxResults — see comment on the traffic-sources query above.
        ).execute()
        device_m_headers = [h["name"] for h in device_m_resp.get("columnHeaders", [])]
        device_by_month = defaultdict(lambda: defaultdict(lambda: {"views": 0, "watch_time_hours": 0.0}))
        for dr in device_m_resp.get("rows", []):
            drow = dict(zip(device_m_headers, dr))
            m = drow.get("day", "")[:7]
            dev = drow.get("deviceType", "")
            bucket = device_by_month[m][dev]
            bucket["views"] += int(drow.get("views", 0))
            bucket["watch_time_hours"] += round(float(drow.get("estimatedMinutesWatched", 0)) / 60, 1)
        for m, by_dev in device_by_month.items():
            rows_m = [{"device": dev, **agg} for dev, agg in by_dev.items()]
            tot = sum(r["views"] for r in rows_m) or 1
            for r in rows_m:
                r["pct"] = round(r["views"] / tot * 100, 1)
            device_by_month[m] = sorted(rows_m, key=lambda r: -r["views"])
        extra["devices_monthly"] = dict(device_by_month)
    except Exception as e:
        print(f"    ⚠  Devices (monthly) fetch failed for {key}: {e}")

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
    monthly = defaultdict(lambda: {"views": 0, "likes": 0, "comments": 0, "count": 0, "shorts": 0, "long_form": 0})
    next_page = None
    for _ in range(10):
        params = {"part": "id", "channelId": channel_id, "type": "video",
                  "order": "date", "maxResults": 50}
        if next_page:
            params["pageToken"] = next_page
        search_resp = ytd.search().list(**params).execute()
        vid_ids = [item["id"]["videoId"] for item in search_resp.get("items", []) if item.get("id", {}).get("videoId")]
        if vid_ids:
            vstats = ytd.videos().list(part="statistics,snippet,contentDetails", id=",".join(vid_ids)).execute()
            for v in vstats.get("items", []):
                pub = v["snippet"]["publishedAt"][:7]
                vs  = v.get("statistics", {})
                dur = _parse_iso8601_duration(v.get("contentDetails", {}).get("duration", ""))
                monthly[pub]["views"]    += int(vs.get("viewCount", 0))
                monthly[pub]["likes"]    += int(vs.get("likeCount", 0))
                monthly[pub]["comments"] += int(vs.get("commentCount", 0))
                monthly[pub]["count"]    += 1
                if dur <= 60:
                    monthly[pub]["shorts"] += 1
                else:
                    monthly[pub]["long_form"] += 1
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
            "videos_published_shorts": d["shorts"],
            "videos_published_long":   d["long_form"],
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
        "user_id":      os.getenv("IG_USER_ID_CARS24_AU"),
        "access_token": os.getenv("IG_ACCESS_TOKEN_CARS24_AU"),
        "handle":       "@cars24au",
    },
    "cars24_uae": {
        "user_id":      os.getenv("IG_USER_ID_CARS24_UAE"),
        "access_token": os.getenv("IG_ACCESS_TOKEN_CARS24_UAE"),
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

def fetch_ig_top_posts(uid: str, tok: str, limit: int = 30) -> list:
    """Fetch recent posts with per-post insights — returns top 20 by reach."""
    import requests
    rows = []
    try:
        # Step 1: recent media basic fields
        r = requests.get(f"{BASE_IG}/{uid}/media", params={
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "limit":  limit,
            "access_token": tok,
        }, timeout=20)
        if not r.ok:
            return []
        media_items = r.json().get("data", [])
    except Exception:
        return []

    for item in media_items:
        mid   = item.get("id", "")
        mtype = item.get("media_type", "")
        ts    = item.get("timestamp", "")[:10]
        cap   = (item.get("caption", "") or "")[:120].replace("\n", " ")
        likes = item.get("like_count", 0)
        cmts  = item.get("comments_count", 0)
        url   = item.get("permalink", "")
        reach = 0
        saves = 0
        shares = 0

        # Step 2: insights per post (reach + saves + shares)
        try:
            metrics = "reach,saved"
            if mtype in ("VIDEO", "REELS"):
                metrics += ",shares"
            ins = requests.get(f"{BASE_IG}/{mid}/insights", params={
                "metric": metrics,
                "access_token": tok,
            }, timeout=10)
            if ins.ok:
                for m in ins.json().get("data", []):
                    name = m.get("name")
                    val  = m.get("values", [{}])[0].get("value", 0) if m.get("values") else m.get("value", 0)
                    if name == "reach":    reach  = val
                    elif name == "saved":  saves  = val
                    elif name == "shares": shares = val
        except Exception:
            pass

        rows.append({
            "post_id":    mid,
            "date":       ts,
            "type":       mtype,
            "caption":    cap,
            "url":        url,
            "likes":      likes,
            "comments":   cmts,
            "reach":      reach,
            "saves":      saves,
            "shares":     shares,
            "interactions": likes + cmts + saves + shares,
        })
        time.sleep(0.15)

    # Sort by reach desc, return top 20
    return sorted(rows, key=lambda x: x["reach"], reverse=True)[:20]

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
            posts = fetch_ig_top_posts(cfg["user_id"], cfg["access_token"])
            if posts:
                write_csv(DATA / f"instagram_{key}_posts.csv", posts)
                print(f"    ✓ top posts: {len(posts)} items")
        except Exception as e:
            print(f"  ✗ {key}: {e}")
        time.sleep(1)

# ── LinkedIn ──────────────────────────────────────────────────────────────────
# Requires: Community Management API product on your LinkedIn Developer App
#   https://www.linkedin.com/developers/apps → Products → Community Management API
# One access token covers all pages the user admins (India, Arabia, Australia).
# Add to .env:
#   LI_ACCESS_TOKEN=AQxxxxxx          (from setup_linkedin_auth.py)
#   LI_ORG_ID_CARS24=1234567
#   LI_ORG_ID_CARS24_ARABIA=1234568
#   LI_ORG_ID_CARS24_AU=1234569

LI_API = "https://api.linkedin.com/v2"

LI_ORGS = {
    "cars24":        os.getenv("LI_ORG_ID_CARS24", ""),
    "cars24_arabia": os.getenv("LI_ORG_ID_CARS24_ARABIA", ""),
    "cars24_au":     os.getenv("LI_ORG_ID_CARS24_AU", ""),
}

def _li_headers():
    tok = os.getenv("LI_ACCESS_TOKEN", "")
    return {
        "Authorization":              f"Bearer {tok}",
        "X-Restli-Protocol-Version":  "2.0.0",
        "LinkedIn-Version":           "202401",
    }

def _li_get(path: str, params: dict = None):
    import requests as req
    r = req.get(f"{LI_API}{path}", headers=_li_headers(), params=params or {}, timeout=15)
    if not r.ok:
        raise Exception(f"HTTP {r.status_code}: {r.text[:200]}")
    return r.json()

def _li_month_ranges(months_back: int = 18):
    """Return list of (start_ms, end_ms) tuples for each of the last N months."""
    from datetime import datetime
    import calendar
    today = datetime.today()
    ranges = []
    yr, mo = today.year, today.month
    for _ in range(months_back):
        mo -= 1
        if mo == 0:
            mo = 12; yr -= 1
    for _ in range(months_back):
        mo += 1
        if mo > 12:
            mo = 1; yr += 1
        _, last_day = calendar.monthrange(yr, mo)
        start_ms = int(datetime(yr, mo, 1).timestamp() * 1000)
        end_ms   = int(datetime(yr, mo, last_day, 23, 59, 59).timestamp() * 1000)
        ranges.append((yr, mo, start_ms, end_ms))
    return ranges

def fetch_li_org(key: str, org_id: str) -> dict:
    """Fetch LinkedIn Page analytics via Community Management API."""
    import requests as req
    results = {"followers_rows": [], "visitor_rows": [], "content_rows": []}
    urn = f"urn:li:organization:{org_id}"
    snap_followers = 0

    # ── 1. Basic org info ──────────────────────────────────────────────────
    try:
        org = _li_get(f"/organizations/{org_id}",
                      {"fields": "localizedName,followersCount"})
        snap_followers = org.get("followersCount", 0)
        org_name = org.get("localizedName", key)
        print(f"    {org_name}: {snap_followers:,} followers")
    except Exception as e:
        print(f"    ! Org lookup failed: {e}")

    month_ranges = _li_month_ranges(18)

    # ── 2. Follower gains — monthly time series ────────────────────────────
    try:
        # Compute running total backwards from snapshot
        fol_rows_raw = []
        for yr, mo, start_ms, end_ms in month_ranges:
            try:
                d = _li_get("/organizationalEntityFollowerStatistics", {
                    "q":                      "organizationalEntity",
                    "organizationalEntity":   urn,
                    "timeIntervals.timeGranularityType": "MONTH",
                    "timeIntervals.timeRange.start": start_ms,
                    "timeIntervals.timeRange.end":   end_ms,
                })
                for el in d.get("elements", []):
                    gains = el.get("followerGains", {})
                    organic = gains.get("organicFollowerGain", 0)
                    paid    = gains.get("paidFollowerGain", 0)
                    fol_rows_raw.append({
                        "yr": yr, "mo": mo,
                        "new": organic + paid,
                        "organic": organic, "paid": paid,
                    })
                    break
            except Exception:
                fol_rows_raw.append({"yr": yr, "mo": mo, "new": 0, "organic": 0, "paid": 0})
            time.sleep(0.2)

        # Reconstruct running total (snap_followers = end of last month)
        running = snap_followers
        for row in reversed(fol_rows_raw):
            mo_str = f"{row['yr']:04d}-{row['mo']:02d}"
            results["followers_rows"].insert(0, {
                "Date":              f"{mo_str}-01",
                "Total Followers":   running,
                "New Followers":     row["new"],
                "Organic Followers": row["organic"],
                "Paid Followers":    row["paid"],
            })
            running = max(0, running - row["new"])

        if results["followers_rows"]:
            print(f"    ✓ Follower time series: {len(results['followers_rows'])} months")
        else:
            raise Exception("no data")
    except Exception as e:
        print(f"    ⚠ Follower stats: {str(e)[:80]}")
        if snap_followers:
            from datetime import date as _date
            t = _date.today()
            results["followers_rows"] = [{
                "Date": f"{t.year}-{t.month:02d}-01",
                "Total Followers": snap_followers,
                "New Followers": "", "Organic Followers": "", "Paid Followers": "",
            }]

    # ── 3. Page / visitor statistics ───────────────────────────────────────
    try:
        for yr, mo, start_ms, end_ms in month_ranges:
            try:
                d = _li_get("/pageStatistics", {
                    "q":                      "pageStatisticsByOrganization",
                    "organizationalEntity":   urn,
                    "timeIntervals.timeGranularityType": "MONTH",
                    "timeIntervals.timeRange.start": start_ms,
                    "timeIntervals.timeRange.end":   end_ms,
                })
                for el in d.get("elements", []):
                    views = el.get("totalPageStatistics", {}).get("views", {})
                    all_v = views.get("allPageViews", {})
                    results["visitor_rows"].append({
                        "Date":                    f"{yr:04d}-{mo:02d}-01",
                        "Total Page Views":        all_v.get("pageViews", 0),
                        "Unique Visitors (total)": all_v.get("uniquePageViews", 0),
                    })
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if results["visitor_rows"]:
            print(f"    ✓ Page views: {len(results['visitor_rows'])} months")
    except Exception as e:
        print(f"    ⚠ Page stats: {str(e)[:80]}")

    # ── 4. Content / share statistics (monthly aggregates) ─────────────────
    try:
        for yr, mo, start_ms, end_ms in month_ranges:
            try:
                d = _li_get("/organizationalEntityShareStatistics", {
                    "q":                      "organizationalEntity",
                    "organizationalEntity":   urn,
                    "timeIntervals.timeGranularityType": "MONTH",
                    "timeIntervals.timeRange.start": start_ms,
                    "timeIntervals.timeRange.end":   end_ms,
                })
                for el in d.get("elements", []):
                    s = el.get("totalShareStatistics", {})
                    imps = s.get("impressionCount", 0)
                    clks = s.get("clickCount", 0)
                    lks  = s.get("likeCount", 0)
                    cmts = s.get("commentCount", 0)
                    shrs = s.get("shareCount", 0)
                    results["content_rows"].append({
                        "Published date": f"{yr:04d}-{mo:02d}-01",
                        "Content Title":  f"Monthly aggregate ({yr:04d}-{mo:02d})",
                        "Impressions":    imps,
                        "Clicks":         clks,
                        "Likes":          lks,
                        "Comments":       cmts,
                        "Shares":         shrs,
                        "Engagement Rate": round((lks+cmts+shrs+clks)/imps, 4) if imps else "",
                    })
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if results["content_rows"]:
            print(f"    ✓ Content stats: {len(results['content_rows'])} months")
    except Exception as e:
        print(f"    ⚠ Content stats: {str(e)[:80]}")

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

    print("\n── Google Search Console ────────────────────────────")
    try:
        import fetch_gsc
        fetch_gsc.main()
    except Exception as e:
        print(f"  ! GSC fetch error: {e}")

    print("\n── GSC Keywords ─────────────────────────────────────")
    try:
        import fetch_gsc_keywords
        fetch_gsc_keywords.main()
    except Exception as e:
        print(f"  ! GSC keywords error: {e}")

    print("\n── BSOS (Share of Search) Sheets ─────────────────────")
    try:
        import fetch_bsos_sheets
        fetch_bsos_sheets.main()
    except Exception as e:
        print(f"  ! BSOS sheets fetch error: {e}")

    print("\n── Google Search Index Sheets ─────────────────────────")
    try:
        import fetch_gindex_sheets
        fetch_gindex_sheets.main()
    except Exception as e:
        print(f"  ! Google Index sheets fetch error: {e}")

    print("\n✅  Done — run: python3 build_data.py")
