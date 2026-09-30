#!/usr/bin/env python3
"""Deploy index.html + feed.xml to toolbox.rss.here.now via the here-now API.

Implements the workspace publish flow: find slug, PUT new version,
upload changed files to presigned URLs, finalize, retry-safe.
Token: ~/.herenow/credentials. Run from the repo root.
"""

import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "https://here.now"
CLIENT = "hermes/rss-universe-deploy"

FILES = [
    ("index.html", "text/html; charset=utf-8"),
    ("feed.xml", "application/rss+xml; charset=utf-8"),
]


def token() -> str:
    return (Path.home() / ".herenow" / "credentials").read_text().strip()


def req(method: str, url: str, *, headers: dict | None = None,
        data: bytes | None = None, timeout: int = 90):
    r = urllib.request.Request(url, method=method, data=data)
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    r.add_header("X-HereNow-Client", CLIENT)
    return urllib.request.urlopen(r, timeout=timeout)


def api(method: str, path: str, body: dict | None = None):
    headers = {
        "Authorization": f"Bearer {token()}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    with req(method, BASE + path, headers=headers, data=data) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    acct = api("GET", "/api/v1/accounts")
    account_id = next(a["id"] for a in acct["accounts"] if a.get("type") == "org")

    pubs = api("GET", "/api/v1/publishes")
    slug = pubs["publishes"][0]["slug"]
    print(f"deploying to slug: {slug}")

    file_specs = []
    for name, ctype in FILES:
        data = (REPO / name).read_bytes()
        file_specs.append((name, ctype, data, hashlib.sha256(data).hexdigest(), len(data)))

    headers = {"Authorization": f"Bearer {token()}",
               "X-HereNow-Account": account_id,
               "Content-Type": "application/json"}
    body = {"files": [
        {"path": n, "size": sz, "contentType": ct, "hash": h}
        for n, ct, _, h, sz in file_specs
    ]}
    upd = api("PUT", f"/api/v1/publish/{slug}", body)
    upload = upd["upload"]
    version_id = upload["versionId"]
    print(f"version {version_id}: upload={len(upload['uploads'])} skipped={len(upload['skipped'])}")

    for entry in upload["uploads"]:
        name = entry["path"]
        data = next(d for n, _, d, _, _ in file_specs if n == name)
        put_headers = {"Content-Type": entry["headers"]["Content-Type"]}
        with req("PUT", entry["url"], headers=put_headers, data=data, timeout=300) as resp:
            code = resp.status
        print(f"uploaded {name}: {code}")
        if code != 200:
            sys.exit(f"upload failed for {name} (HTTP {code}); NOT finalizing")

    body = json.dumps({"versionId": version_id}).encode()
    for attempt in range(5):
        try:
            with req("POST", upload["finalizeUrl"], headers=headers, data=body,
                     timeout=120) as resp:
                fin = json.loads(resp.read().decode())
            print(f"finalized: {json.dumps(fin)}")
            return
        except Exception as e:  # noqa: BLE001 - finalize timeouts are known-flaky
            print(f"finalize attempt {attempt + 1} failed: {e}; retrying in 20s")
            time.sleep(20)
    sys.exit("finalize failed after retries — check dashboard before re-running")


if __name__ == "__main__":
    main()
