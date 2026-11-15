"""One-time: turn a short-lived Meta token into a permanent Page token and
save it (plus the Instagram and Page ids) as GitHub Actions secrets.

Run:  .venv/bin/python scripts/setup_meta.py
Nothing you type here is printed or written to disk.
"""
import getpass, subprocess, sys

import requests

G = "https://graph.facebook.com/v24.0"


def get(url, **params):
    r = requests.get(url, params=params, timeout=60)
    d = r.json()
    if "error" in d:
        sys.exit(f"Meta said: {d['error'].get('message')}")
    return d


app_id = input("App ID: ").strip()
app_secret = getpass.getpass("App Secret (hidden): ").strip()
short = getpass.getpass("User token from Graph API Explorer (hidden): ").strip()

long_user = get(f"{G}/oauth/access_token", grant_type="fb_exchange_token", client_id=app_id,
                client_secret=app_secret, fb_exchange_token=short)["access_token"]
pages = get(f"{G}/me/accounts", fields="name,id,access_token,instagram_business_account{id,username}",
            access_token=long_user).get("data", [])
pages = [p for p in pages if p.get("instagram_business_account")]
if not pages:
    sys.exit("No Facebook Page with a linked Instagram professional account was found. "
             "Link them in Instagram > Settings > Accounts Centre, then try again.")
for i, p in enumerate(pages):
    print(f"[{i}] {p['name']}  ->  @{p['instagram_business_account'].get('username')}")
p = pages[int(input("Which one? number: ").strip() or 0)] if len(pages) > 1 else pages[0]

info = get(f"{G}/debug_token", input_token=p["access_token"], access_token=f"{app_id}|{app_secret}")["data"]
need = {"instagram_content_publish", "pages_manage_posts"}
missing = need - set(info.get("scopes", []))
if missing:
    sys.exit(f"Token is missing permissions: {', '.join(sorted(missing))}. Add them and generate again.")
print("Token expires:", "never" if not info.get("expires_at") else info["expires_at"])

for name, val in (("META_TOKEN", p["access_token"]), ("IG_USER_ID", p["instagram_business_account"]["id"]),
                  ("FB_PAGE_ID", p["id"])):
    subprocess.run(["gh", "secret", "set", name], input=val, text=True, check=True)
print(f"Saved. Page '{p['name']}' and @{p['instagram_business_account'].get('username')} are connected.")
