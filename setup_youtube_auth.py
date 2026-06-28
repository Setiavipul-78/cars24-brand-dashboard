#!/usr/bin/env python3
"""
One-time OAuth setup for YouTube Analytics API.
Run this once locally to get a refresh token saved to .env.

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create project → Enable YouTube Data API v3 + YouTube Analytics API
  3. OAuth consent screen → External → Add your email as test user
  4. Credentials → Create OAuth client ID → Desktop app → Download JSON
  5. Save as credentials.json in this directory
  6. Run: python3 setup_youtube_auth.py
"""

import os
import json
from pathlib import Path

CREDS_FILE = Path("credentials.json")
ENV_FILE = Path(".env")

def main():
    if not CREDS_FILE.exists():
        print("""
  ✗  credentials.json not found.

  Steps to create it:
  1. Go to https://console.cloud.google.com/
  2. New project → APIs & Services → Enable:
       - YouTube Data API v3
       - YouTube Analytics API
  3. OAuth consent screen → External → Add your email as test user
  4. Credentials → + Create Credentials → OAuth client ID → Desktop app
  5. Download the JSON → save it as credentials.json here
  Then re-run this script.
""")
        return

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("  ! Install: pip install google-auth-oauthlib google-api-python-client")
        return

    SCOPES = [
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]

    print("\n  Opening browser for Google OAuth…")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    # Extract client ID/secret from credentials.json
    with open(CREDS_FILE) as f:
        c = json.load(f)["installed"]

    refresh_token = creds.refresh_token
    client_id = c["client_id"]
    client_secret = c["client_secret"]

    print(f"""
  ✓  Auth successful!
     Refresh token: {refresh_token[:30]}…
""")

    # Read existing .env
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    existing["GOOGLE_CLIENT_ID"] = client_id
    existing["GOOGLE_CLIENT_SECRET"] = client_secret
    existing["YT_REFRESH_TOKEN"] = refresh_token

    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    print(f"  ✓  .env updated with GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, YT_REFRESH_TOKEN")
    print("\n  Next steps:")
    print("    1. Add channel IDs to .env (see .env.example)")
    print("    2. Add Instagram credentials to .env")
    print("    3. Run: python3 fetch_social.py")

if __name__ == "__main__":
    main()
