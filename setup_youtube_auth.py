#!/usr/bin/env python3
"""
One-time OAuth setup for YouTube Analytics API.
Run this once per account to save a refresh token to .env.

Usage:
  python3 setup_youtube_auth.py              # sets YT_REFRESH_TOKEN (Cars24 AU)
  python3 setup_youtube_auth.py --account uae  # sets YT_REFRESH_TOKEN_UAE
  python3 setup_youtube_auth.py --account au   # sets YT_REFRESH_TOKEN_AU (same as default)

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create project → Enable YouTube Data API v3 + YouTube Analytics API
  3. OAuth consent screen → External → Add your email as test user
  4. Credentials → Create OAuth client ID → Desktop app → Download JSON
  5. Save as credentials.json in this directory
"""

import os
import sys
import json
import argparse
from pathlib import Path

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

CREDS_FILE = Path("credentials.json")
ENV_FILE = Path(".env")

ACCOUNT_CONFIG = {
    "au": {
        "token_key": "YT_REFRESH_TOKEN",
        "login_hint": "vipul.setia@cars24.com",
        "label": "Cars24 AU",
    },
    "uae": {
        "token_key": "YT_REFRESH_TOKEN_UAE",
        "login_hint": "cars24.uaesocial@cars24.com",
        "label": "Cars24 UAE",
    },
    "india": {
        "token_key": "YT_REFRESH_TOKEN_INDIA",
        "login_hint": "cars24india1@gmail.com",
        "label": "Cars24 India",
    },
    "teambhp": {
        "token_key": "YT_REFRESH_TOKEN_TEAMBHP",
        "login_hint": "cars24india1@gmail.com",
        "label": "TeamBHP",
    },
    "insider": {
        "token_key": "YT_REFRESH_TOKEN_INSIDER",
        "login_hint": "Cars24.tamil@cars24.com",
        "label": "Cars24 Insider",
    },
    "tamil": {
        "token_key": "YT_REFRESH_TOKEN_MALAYALAM",
        "login_hint": "vipul.setia@cars24.com",
        "label": "Cars24 Tamil (+ Malayalam)",
    },
    "malayalam2": {
        "token_key": "YT_REFRESH_TOKEN_MALAYALAM2",
        "login_hint": "vipul.setia@cars24.com",
        "label": "Cars24 Malayalam",
    },
    "malayalam": {
        "token_key": "YT_REFRESH_TOKEN_MALAYALAM",
        "login_hint": "Cars24.tamil@cars24.com",
        "label": "Cars24 Malayalam",
    },
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default="au", choices=list(ACCOUNT_CONFIG.keys()),
                        # au | uae | india | teambhp | insider | tamil | malayalam
                        help="Which account to authenticate")
    parser.add_argument("--email", default=None,
                        help="Google account email to pre-fill in browser login")
    args = parser.parse_args()

    cfg = ACCOUNT_CONFIG[args.account]
    token_key = cfg["token_key"]
    login_hint = args.email or cfg["login_hint"]
    label = cfg["label"]

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
    except ImportError:
        print("  ! Install: pip install google-auth-oauthlib google-api-python-client")
        return

    SCOPES = [
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    print(f"\n  Opening browser for Google OAuth — {label}")
    if login_hint:
        print(f"  Account hint: {login_hint}")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    server_kwargs = dict(
        port=0,
        open_browser=True,
        authorization_prompt_message='',
        prompt='select_account',
    )
    if login_hint:
        server_kwargs["login_hint"] = login_hint

    creds = flow.run_local_server(**server_kwargs)

    with open(CREDS_FILE) as f:
        c = json.load(f)["installed"]

    refresh_token = creds.refresh_token
    client_id = c["client_id"]
    client_secret = c["client_secret"]

    print(f"""
  ✓  Auth successful for {label}!
     Token key: {token_key}
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
    existing[token_key] = refresh_token

    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    print(f"  ✓  .env updated: {token_key}")
    print(f"\n  Next steps:")
    print(f"    python3 fetch_social.py")

if __name__ == "__main__":
    main()
