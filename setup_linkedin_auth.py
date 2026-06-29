#!/usr/bin/env python3
"""
LinkedIn OAuth setup — Cars24 Dashboard
Pulls: follower trends, page views, content impressions/engagement

Prerequisites (one-time, ~5 minutes):
  1. Go to https://www.linkedin.com/developers/apps → Create App
       - App name: Cars24 Dashboard
       - LinkedIn Page: choose any Cars24 page (India is fine)
       - App logo: optional
  2. Under the app → Products tab → request:
       "Community Management API"   ← approve is usually instant/same day
       (NOT Marketing Developer Platform — that takes weeks)
  3. Under Auth tab:
       - Copy Client ID and Client Secret
       - Add Redirect URL: http://localhost:8765/callback
  4. Run this script:
       python3 setup_linkedin_auth.py

After OAuth completes, the script discovers all LinkedIn Pages you admin
and prints their org IDs — add them to .env.
"""

import os, json, webbrowser, urllib.parse, http.server, threading, time
from pathlib import Path

try:
    import requests
except ImportError:
    os.system("pip3 install requests -q")
    import requests

ENV_FILE  = Path(".env")
PORT      = 8765
REDIRECT  = f"http://localhost:{PORT}/callback"
AUTH_BASE = "https://www.linkedin.com/oauth/v2"
API_BASE  = "https://api.linkedin.com/v2"

def env_update(updates: dict):
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    existing.update(updates)
    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")

_auth_code = None

class _CB(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in qs:
            _auth_code = qs["code"][0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b"<h2 style='font-family:sans-serif'>Authorised! You can close this tab.</h2>")
        else:
            err = qs.get("error_description", ["Unknown"])[0]
            self.send_response(400); self.end_headers()
            self.wfile.write(f"<h2>Auth failed: {err}</h2>".encode())
    def log_message(self, *a): pass

def _run_server():
    srv = http.server.HTTPServer(("", PORT), _CB)
    srv.timeout = 180
    srv.handle_request()
    srv.server_close()

def li_get(tok, path, params=None):
    r = requests.get(f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {tok}",
                 "X-Restli-Protocol-Version": "2.0.0",
                 "LinkedIn-Version": "202401"},
        params=params or {}, timeout=15)
    r.raise_for_status()
    return r.json()

def main():
    print("\n── LinkedIn OAuth Setup ─────────────────────────────────────────")

    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

    client_id     = os.getenv("LI_CLIENT_ID") or input("  Client ID:     ").strip()
    client_secret = os.getenv("LI_CLIENT_SECRET") or input("  Client Secret: ").strip()
    if not client_id or not client_secret:
        print("  ✗  Client ID and Secret required. Get them from:")
        print("     https://www.linkedin.com/developers/apps")
        return

    scopes = " ".join([
        "r_basicprofile",
        "r_emailaddress",
        "r_organization_social",   # follower + page + content stats (Community Management API)
        "rw_organization_admin",   # page management
        "w_member_social",
    ])

    auth_url = (
        f"{AUTH_BASE}/authorization?response_type=code"
        f"&client_id={urllib.parse.quote(client_id)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT)}"
        f"&scope={urllib.parse.quote(scopes)}"
        f"&state=cars24dash"
    )

    print(f"\n  Starting callback server on port {PORT}...")
    threading.Thread(target=_run_server, daemon=True).start()
    print(f"  Opening browser for LinkedIn login...\n")
    webbrowser.open(auth_url)

    deadline = time.time() + 180
    while _auth_code is None and time.time() < deadline:
        time.sleep(0.5)

    if not _auth_code:
        print("  ✗  Timed out. Try again.")
        return

    print("  ✓  Got auth code — exchanging for token...")
    r = requests.post(f"{AUTH_BASE}/accessToken", data={
        "grant_type":    "authorization_code",
        "code":          _auth_code,
        "redirect_uri":  REDIRECT,
        "client_id":     client_id,
        "client_secret": client_secret,
    }, timeout=15)

    if not r.ok:
        print(f"  ✗  Token exchange failed: {r.status_code} {r.text[:200]}")
        return

    tok_data = r.json()
    tok = tok_data["access_token"]
    days = tok_data.get("expires_in", 0) // 86400
    print(f"  ✓  Token obtained (expires in {days} days)\n")

    # Who logged in
    try:
        me = li_get(tok, "/me")
        name = f"{me.get('localizedFirstName','')} {me.get('localizedLastName','')}".strip()
        print(f"  Logged in as: {name}")
    except Exception as e:
        print(f"  (Could not fetch profile: {e})")

    # Discover all managed Pages
    print("\n  Discovering LinkedIn Pages you admin...")
    orgs_found = []
    try:
        acls = requests.get(f"{API_BASE}/organizationAcls",
            headers={"Authorization": f"Bearer {tok}", "X-Restli-Protocol-Version": "2.0.0"},
            params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED",
                    "projection": "(elements*(organization~(localizedName,followersCount)))"},
            timeout=15)
        elements = acls.json().get("elements", []) if acls.ok else []
        for el in elements:
            urn = el.get("organization", "")
            org_id = urn.split(":")[-1] if ":" in urn else ""
            try:
                info = li_get(tok, f"/organizations/{org_id}",
                              {"fields": "localizedName,followersCount"})
                org_name = info.get("localizedName", org_id)
                followers = info.get("followersCount", "?")
                print(f"    • {org_name:<35} ID: {org_id:<12} Followers: {followers:,}" if isinstance(followers, int) else f"    • {org_name:<35} ID: {org_id}")
                orgs_found.append((org_id, org_name))
            except Exception:
                print(f"    • (org {org_id})")
                orgs_found.append((org_id, org_id))
    except Exception as e:
        print(f"  ! Could not list orgs: {e}")

    # Save credentials
    updates = {
        "LI_CLIENT_ID":     client_id,
        "LI_CLIENT_SECRET": client_secret,
        "LI_ACCESS_TOKEN":  tok,
    }
    env_update(updates)
    print(f"\n  ✓  LI_ACCESS_TOKEN saved to .env")

    if orgs_found:
        print("\n  ── Add the org IDs below to .env ───────────────────────────────")
        for org_id, org_name in orgs_found:
            guess_key = org_name.lower().replace(" ", "_").replace("-", "_")
            print(f"  # {org_name}")
            print(f"  LI_ORG_ID_{guess_key.upper()}={org_id}")
        print()
        print("  For Cars24 Arabia:    LI_ORG_ID_CARS24_ARABIA=<id>")
        print("  For Cars24 Australia: LI_ORG_ID_CARS24_AU=<id>")
    else:
        print("\n  No managed pages found — make sure you're logged in with the right account.")
        print("  Find org IDs from LinkedIn Page URL: linkedin.com/company/<org-id>/")

    print(f"""
  ── Next steps ──────────────────────────────────────────────────────
  1. Add org IDs to .env (see above)
  2. python3 fetch_social.py
  3. python3 build_data.py
  ────────────────────────────────────────────────────────────────────
""")

if __name__ == "__main__":
    main()
