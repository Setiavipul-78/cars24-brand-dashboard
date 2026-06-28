#!/usr/bin/env python3
"""
Fetch live social media metrics for Cars24 brand dashboard.

Pulls from:
  • YouTube Analytics API v2  — views, subscribers, watch time, CTR (monthly)
  • Instagram Graph API       — followers, reach, impressions, profile views (monthly)

Output CSVs in data/:
  youtube_cars24_india.csv, youtube_teambhp.csv, youtube_cars24_insider.csv
  youtube_cars24_au.csv, youtube_cars24_uae.csv
  instagram_cars24_india.csv, instagram_teambhp.csv
  instagram_cars24_au.csv, instagram_cars24_uae.csv

Usage:
  1. Complete setup once:  python3 setup_youtube_auth.py
  2. Fill .env with Instagram credentials (see .env.example)
  3. Run:  python3 fetch_social.py
  4. Then: python3 build_data.py
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

def get_yt_credentials():
    """Build OAuth2 credentials from stored refresh token."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        print("  ! Run: pip install google-api-python-client google-auth-oauthlib")
        return None

    creds = Credentials(
        token=None,
        refresh_token=os.getenv("YT_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/yt-analytics.readonly",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
    )
    try:
        creds.refresh(Request())
        return creds
    except Exception as e:
        print(f"  ! OAuth refresh failed: {e}\n    Run: python3 setup_youtube_auth.py")
        return None

def fetch_yt_channel(key: str, channel_id: str, creds) -> list[dict]:
    """Pull monthly analytics for one YouTube channel."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return []

    if not channel_id:
        print(f"  ! No channel ID set for {key}  (add YT_CHANNEL_ID_{key.upper()} to .env)")
        return []

    yta = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    ytd = build("youtube", "v3", credentials=creds, cache_discovery=False)

    # Channel snapshot
    snap = ytd.channels().list(part="statistics", id=channel_id).execute()
    stats = snap["items"][0]["statistics"] if snap.get("items") else {}
    total_subs = int(stats.get("subscriberCount", 0))
    total_views = int(stats.get("viewCount", 0))
    total_videos = int(stats.get("videoCount", 0))

    # Monthly analytics — last 24 months
    start = datetime(datetime.today().year - 2, 1, 1).strftime("%Y-%m-%d")
    end = date.today().strftime("%Y-%m-%d")
    resp = yta.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start, endDate=end,
        dimensions="month",
        metrics=",".join([
            "views", "estimatedMinutesWatched", "averageViewDuration",
            "subscribersGained", "subscribersLost",
            "likes", "comments", "shares",
            "impressions", "impressionsClickThroughRate",
        ]),
        sort="month",
    ).execute()

    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = []
    for r in resp.get("rows", []):
        row = dict(zip(headers, r))
        m = row.get("month", "")[:7]  # "YYYY-MM"
        subs_gained = int(row.get("subscribersGained", 0))
        subs_lost = int(row.get("subscribersLost", 0))
        rows.append({
            "month":             m,
            "label":             mlabel(m),
            "views":             int(row.get("views", 0)),
            "watch_time_hours":  round(float(row.get("estimatedMinutesWatched", 0)) / 60, 1),
            "avg_view_duration": round(float(row.get("averageViewDuration", 0)), 0),
            "subscribers_gained": subs_gained,
            "subscribers_lost":  subs_lost,
            "net_subs":          subs_gained - subs_lost,
            "likes":             int(row.get("likes", 0)),
            "comments":          int(row.get("comments", 0)),
            "shares":            int(row.get("shares", 0)),
            "impressions":       int(row.get("impressions", 0)),
            "ctr":               round(float(row.get("impressionsClickThroughRate", 0)), 2),
            "total_subscribers": total_subs,
            "total_views":       total_views,
            "total_videos":      total_videos,
        })
    return rows

def fetch_all_youtube():
    print("\n── YouTube ──────────────────────────────────────────")
    missing = [k for k, v in YT_CHANNELS.items() if v]
    if not missing:
        print("  ! No YT_CHANNEL_ID_* vars set in .env — skipping YouTube")
        return

    creds = get_yt_credentials()
    if not creds:
        return

    for key, channel_id in YT_CHANNELS.items():
        if not channel_id:
            continue
        print(f"  Fetching {key}…")
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

    # Monthly insights — Instagram allows since/until for period=month
    monthly_metrics = [
        "impressions", "reach", "profile_views",
        "email_contacts", "phone_call_clicks", "website_clicks",
    ]

    # Build list of months from 24 months ago to today
    today = date.today()
    months = []
    for i in range(24, 0, -1):
        yr = today.year - (today.month - i - 1) // 12 - 1 if (today.month - i) <= 0 else today.year
        mo = (today.month - i - 1) % 12 + 1 if (today.month - i) <= 0 else today.month - i
        mo = ((today.month - 1 - i) % 12) + 1
        yr = today.year + ((today.month - 1 - i) // 12)
        months.append(f"{yr:04d}-{mo:02d}")
    months = sorted(set(months))[-24:]

    rows = []
    for m in months:
        # since/until for this month
        yr, mo = int(m[:4]), int(m[5:7])
        since_ts = int(datetime(yr, mo, 1).timestamp())
        if mo == 12:
            until_ts = int(datetime(yr + 1, 1, 1).timestamp())
        else:
            until_ts = int(datetime(yr, mo + 1, 1).timestamp())

        try:
            data = ig_get(f"/{uid}/insights", {
                "metric":       ",".join(monthly_metrics),
                "period":       "month",
                "since":        since_ts,
                "until":        until_ts,
                "access_token": tok,
            })
        except Exception as e:
            print(f"    ⚠  {m}: {e}")
            continue

        met = {item["name"]: item["values"][0]["value"] if item.get("values") else 0
               for item in data.get("data", [])}

        # Follower count for this month — use period=day and take end-of-month
        try:
            fc_data = ig_get(f"/{uid}/insights", {
                "metric":       "follower_count",
                "period":       "day",
                "since":        until_ts - 86400,
                "until":        until_ts,
                "access_token": tok,
            })
            followers_eom = 0
            followers_gained = 0
            for item in fc_data.get("data", []):
                if item["name"] == "follower_count":
                    vals = item.get("values", [])
                    if vals:
                        followers_eom = vals[-1].get("value", 0)
                        if len(vals) >= 2:
                            followers_gained = max(0, vals[-1].get("value", 0) - vals[0].get("value", 0))
        except Exception:
            followers_eom = 0
            followers_gained = 0

        rows.append({
            "month":             m,
            "label":             mlabel(m),
            "followers":         followers_eom or total_followers,
            "followers_gained":  followers_gained,
            "reach":             met.get("reach", 0),
            "impressions":       met.get("impressions", 0),
            "profile_views":     met.get("profile_views", 0),
            "email_contacts":    met.get("email_contacts", 0),
            "phone_clicks":      met.get("phone_call_clicks", 0),
            "website_clicks":    met.get("website_clicks", 0),
            "accounts_engaged":  met.get("accounts_engaged", 0),
            "total_followers":   total_followers,
            "total_media":       total_media,
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

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("═══ fetch_social.py ═══")
    fetch_all_youtube()
    fetch_all_instagram()
    print("\n✅  Done — run: python3 build_data.py")
