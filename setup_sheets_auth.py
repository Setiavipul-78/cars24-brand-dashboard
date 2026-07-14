#!/usr/bin/env python3
"""
One-time OAuth for Google Sheets read access.
Run once to save SHEETS_REFRESH_TOKEN to .env.
"""
import os, json
from pathlib import Path

CREDS_FILE = Path("credentials.json")
ENV_FILE   = Path(".env")
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def main():
    from google_auth_oauthlib.flow import InstalledAppFlow
    print("\n  Opening browser — sign in with vipul.setia@cars24.com\n")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(
        port=8766, open_browser=True,
        authorization_prompt_message='',
        prompt='select_account consent',
        access_type='offline',
        login_hint='vipul.setia@cars24.com',
    )
    rt = creds.refresh_token
    if not rt:
        print("  ✗ No refresh token — revoke app access at myaccount.google.com/permissions and retry")
        return
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing["SHEETS_REFRESH_TOKEN"] = rt
    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    print(f"  ✓ SHEETS_REFRESH_TOKEN saved to .env")

if __name__ == "__main__":
    main()
