#!/usr/bin/env python3
"""
One-time OAuth setup for Google Search Console API.
Run once to save a refresh token to .env.

Usage:
  python3 setup_gsc_auth.py

Prerequisites:
  credentials.json must exist (same file used for YouTube OAuth)
"""

import os
import json
from pathlib import Path

CREDS_FILE = Path("credentials.json")
ENV_FILE   = Path(".env")
SCOPES     = ["https://www.googleapis.com/auth/webmasters.readonly"]

def main():
    if not CREDS_FILE.exists():
        print("""
  ✗  credentials.json not found.
     Use the same credentials.json from your YouTube OAuth setup.
""")
        return

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("  ! Install: pip install google-auth-oauthlib")
        return

    print("\n  Opening browser for Google OAuth — Google Search Console")
    print("  Sign in with: vipul.setia@cars24.com")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(
        port=8765,
        open_browser=True,
        authorization_prompt_message='',
        prompt='select_account consent',
        access_type='offline',
        login_hint='vipul.setia@cars24.com',
    )

    refresh_token = creds.refresh_token
    if not refresh_token:
        print("  ✗  No refresh token returned.")
        print("     Revoke app access at https://myaccount.google.com/permissions then retry.")
        return

    with open(CREDS_FILE) as f:
        c = json.load(f)["installed"]

    print(f"""
  ✓  GSC auth successful!
     Refresh token: {refresh_token[:30]}…
""")

    # Read existing .env
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    existing["GOOGLE_CLIENT_ID"]     = c["client_id"]
    existing["GOOGLE_CLIENT_SECRET"] = c["client_secret"]
    existing["GSC_REFRESH_TOKEN"]    = refresh_token

    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

    print("  ✓  .env updated with GSC_REFRESH_TOKEN")
    print("\n  Next step:")
    print("    python3 fetch_gsc.py --full")

if __name__ == "__main__":
    main()
