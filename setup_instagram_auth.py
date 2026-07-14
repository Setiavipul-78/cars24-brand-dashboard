#!/usr/bin/env python3
"""
One-time Instagram Graph API setup for Cars24 brand dashboard.
Run this once to get access tokens and Instagram Business Account IDs.

Prerequisites:
  1. Go to https://developers.facebook.com/apps → Create App → Consumer type
  2. Add product: Instagram Graph API
  3. Under Instagram → Basic Display OR Instagram Graph API settings,
     add your Instagram test user (your IG handle)
  4. Copy your App ID and App Secret from App Settings → Basic
  5. Run: python3 setup_instagram_auth.py
"""

import os, json, time, urllib.parse, webbrowser
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"))

ENV_FILE = Path(".env")
BASE = "https://graph.facebook.com/v19.0"
REDIRECT_URI = "https://www.facebook.com/connect/login_success.html"

# ── Helpers ───────────────────────────────────────────────────────────────────
def env_set(key: str, val: str):
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing[key] = val
    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

def fb_get(path, params):
    import urllib.request, ssl
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, context=ctx, timeout=15) as r:
        return json.loads(r.read())

# ── Main flow ─────────────────────────────────────────────────────────────────
def main():
    print("\n-- Instagram Graph API Setup ------------------------------------")

    app_id     = os.getenv("META_APP_ID") or input("\n  Enter your Meta App ID:     ").strip()
    app_secret = os.getenv("META_APP_SECRET") or input("  Enter your Meta App Secret: ").strip()

    if not app_id or not app_secret:
        print("  X  App ID and Secret are required.")
        return

    scopes = ",".join([
        "pages_show_list",
        "pages_read_engagement",
        "instagram_basic",
        "instagram_manage_insights",
        "business_management",
    ])

    auth_url = (
        f"https://www.facebook.com/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={scopes}"
        f"&response_type=code"
    )

    print(f"\n  Opening browser for Facebook login...")
    print(f"  After you click Allow, the browser will redirect to a blank Facebook page.")
    print(f"  Copy the FULL URL from the address bar and paste it below.\n")
    webbrowser.open(auth_url)

    redirected_url = input("  Paste the full redirect URL here: ").strip()

    parsed = urllib.parse.urlparse(redirected_url)
    params = urllib.parse.parse_qs(parsed.query)
    # Also check fragment for token flows
    frag_params = urllib.parse.parse_qs(parsed.fragment)

    if "code" not in params:
        print(f"  X  No auth code found in URL. Got: {params}")
        return

    auth_code = params["code"][0]
    print("  OK  Got auth code - exchanging for access token...")

    # Exchange code for short-lived user token
    try:
        tok_data = fb_get("/oauth/access_token", {
            "client_id":     app_id,
            "client_secret": app_secret,
            "redirect_uri":  REDIRECT_URI,
            "code":          auth_code,
        })
        short_token = tok_data["access_token"]
    except Exception as e:
        print(f"  X  Token exchange failed: {e}")
        return

    print("  OK  Short-lived token obtained - extending to 60 days...")

    # Exchange code for short-lived user token
    try:
        tok_data = fb_get("/oauth/access_token", {
            "client_id":     app_id,
            "client_secret": app_secret,
            "redirect_uri":  redirect_uri,
            "code":          _auth_code,
        })
        short_token = tok_data["access_token"]
    except Exception as e:
        print(f"  ✗  Token exchange failed: {e}")
        return

    # Exchange for long-lived token (60 days)
    try:
        ll_data = fb_get("/oauth/access_token", {
            "grant_type":        "fb_exchange_token",
            "client_id":         app_id,
            "client_secret":     app_secret,
            "fb_exchange_token": short_token,
        })
        long_token = ll_data["access_token"]
        expires_in = ll_data.get("expires_in", 0)
        print(f"  ✓  Long-lived token obtained (expires in {expires_in//86400} days)")
    except Exception as e:
        print(f"  ✗  Long-lived token exchange failed: {e}")
        long_token = short_token

    # Get Facebook Pages the user manages
    try:
        pages = fb_get("/me/accounts", {"access_token": long_token})
        page_list = pages.get("data", [])
    except Exception as e:
        print(f"  ✗  Could not list Pages: {e}")
        return

    if not page_list:
        print("  ✗  No Facebook Pages found. Make sure the account manages a Page.")
        return

    print(f"\n  Found {len(page_list)} Facebook Page(s):\n")

    ig_accounts = []
    for page in page_list:
        page_id   = page["id"]
        page_name = page["name"]
        page_tok  = page.get("access_token", long_token)

        try:
            ig_data = fb_get(f"/{page_id}", {
                "fields":       "instagram_business_account",
                "access_token": page_tok,
            })
            ig_biz = ig_data.get("instagram_business_account", {})
            ig_id  = ig_biz.get("id")

            if ig_id:
                # Get IG account name
                ig_info = fb_get(f"/{ig_id}", {
                    "fields":       "username,followers_count",
                    "access_token": page_tok,
                })
                handle = ig_info.get("username", "unknown")
                followers = ig_info.get("followers_count", "?")
                print(f"    ✓  {page_name:30s} → @{handle} ({followers:,} followers)  IG ID: {ig_id}")
                ig_accounts.append({
                    "key":     handle.lower().replace(".", "_"),
                    "ig_id":   ig_id,
                    "handle":  handle,
                    "page_tok": page_tok,
                    "name":    page_name,
                })
            else:
                print(f"    –  {page_name:30s} → no Instagram account linked")
        except Exception as e:
            print(f"    ✗  {page_name}: {e}")

    if not ig_accounts:
        print("\n  ✗  No Instagram Business Accounts found.")
        print("     Make sure Instagram is linked to a Facebook Page via:")
        print("     Facebook Page → Settings → Linked accounts → Instagram")
        return

    # Save to .env
    print("\n  Saving to .env…")
    env_set("META_APP_ID", app_id)
    env_set("META_APP_SECRET", app_secret)
    env_set("IG_ACCESS_TOKEN", long_token)

    # Match known handles to .env key names
    handle_map = {
        "cars24india":   "IG_USER_ID_CARS24_INDIA",
        "cars24":        "IG_USER_ID_CARS24_INDIA",
        "teambhp":       "IG_USER_ID_TEAMBHP",
        "cars24au":      "IG_USER_ID_AU",
        "cars24uae":     "IG_USER_ID_UAE",
        "cars24malayalam": "IG_USER_ID_CARS24_MALAYALAM",
    }

    for acc in ig_accounts:
        slug = acc["handle"].lower().replace(".", "").replace("_", "").replace("-", "")
        env_key = handle_map.get(slug, f"IG_USER_ID_{acc['handle'].upper()}")
        env_set(env_key, acc["ig_id"])
        print(f"  ✓  {env_key} = {acc['ig_id']}")

    print(f"""
  ✓  All done! {len(ig_accounts)} Instagram account(s) configured.

  Next steps:
    1. Run: python3 fetch_social.py
    2. Run: python3 build_data.py
    3. Refresh the dashboard

  Note: Long-lived tokens expire in ~60 days. Re-run this script to refresh.
""")

if __name__ == "__main__":
    main()
