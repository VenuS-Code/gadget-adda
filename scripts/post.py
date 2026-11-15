"""Publish out/reel.mp4 as an Instagram Reel and a Facebook Page Reel.

Needs env: META_TOKEN (Page access token), IG_USER_ID, FB_PAGE_ID.
Records each success in posted.json so a re-run never double-posts.
"""
import datetime, json, os, sys, time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
G = "https://graph.facebook.com/v24.0"
TOKEN = os.environ.get("META_TOKEN", "").strip()
IG = os.environ.get("IG_USER_ID", "").strip()
PAGE = os.environ.get("FB_PAGE_ID", "").strip()
VIDEO = ROOT / "out/reel.mp4"
LOG = ROOT / "posted.json"


def call(method, url, **kw):
    r = requests.request(method, url, timeout=300, **kw)
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:300]}
    if r.status_code >= 400 or (isinstance(data, dict) and "error" in data):
        raise RuntimeError(f"{method} {url.split('?')[0]} -> {r.status_code}: {json.dumps(data)[:500]}")
    return data


def upload(url):
    size = VIDEO.stat().st_size
    with open(VIDEO, "rb") as fh:
        return call("POST", url, data=fh, headers={
            "Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(size)})


def post_instagram(caption):
    c = call("POST", f"{G}/{IG}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": "true", "access_token": TOKEN})
    upload(c["uri"])
    for _ in range(40):
        st = call("GET", f"{G}/{c['id']}", params={"fields": "status_code,status", "access_token": TOKEN})
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram rejected the video: {st}")
        time.sleep(15)
    else:
        raise RuntimeError("Instagram processing timed out")
    return call("POST", f"{G}/{IG}/media_publish", data={"creation_id": c["id"], "access_token": TOKEN})["id"]


def post_facebook(caption):
    s = call("POST", f"{G}/{PAGE}/video_reels", data={"upload_phase": "start", "access_token": TOKEN})
    upload(s["upload_url"])
    call("POST", f"{G}/{PAGE}/video_reels", data={
        "upload_phase": "finish", "video_id": s["video_id"], "video_state": "PUBLISHED",
        "description": caption, "access_token": TOKEN})
    return s["video_id"]


def main():
    if not (TOKEN and IG and PAGE):
        sys.exit("Missing META_TOKEN / IG_USER_ID / FB_PAGE_ID. Run scripts/setup_meta.py first.")
    meta = json.loads((ROOT / "out/meta.json").read_text())
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    entry = log.setdefault(str(meta["day"]), {"product_id": meta["product_id"]})
    errors = []
    for name, fn in (("instagram", post_instagram), ("facebook", post_facebook)):
        if entry.get(name):
            print(f"{name}: already posted, skipping")
            continue
        try:
            entry[name] = fn(meta["caption"])
            entry[name + "_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            print(f"{name}: posted {entry[name]}")
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"{name}: FAILED {e}")
        LOG.write_text(json.dumps(log, indent=1))
    if errors:
        sys.exit("\n".join(errors))


if __name__ == "__main__":
    main()
