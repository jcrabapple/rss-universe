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
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "https://here.now"
CLIENT = "hermes/rss-universe-deploy"
# The rss workspace (org) owns the site; the label toolbox.rss.here.now maps to it.
ORG_ACCOUNT_ID = "7b096eba-974b-4876-9077-d0445e04d91c"

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


def api(method: str, path: str, body: dict | None = None, extra: dict | None = None):
    headers = {
        "Authorization": f"Bearer {token()}",
        "Content-Type": "application/json",
        **(extra or {}),
    }
    data = json.dumps(body).encode() if body is not None else None
    with req(method, BASE + path, headers=headers, data=data) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    acct = api("GET", "/api/v1/accounts")
    org = next(a["accountId"] for a in acct["accounts"]
               if a["accountId"] == ORG_ACCOUNT_ID and a.get("type") == "org")

    ws_headers = {"X-HereNow-Account": org}
    pubs = api("GET", "/api/v1/publishes", extra=ws_headers)
    assert len(pubs["publishes"]) == 1, f"expected 1 publish in workspace, got {len(pubs['publishes'])}"
    slug = pubs["publishes"][0]["slug"]
    print(f"deploying to slug: {slug}")

    file_specs = []
    for name, ctype in FILES:
        data = (REPO / name).read_bytes()
        file_specs.append((name, ctype, data, hashlib.sha256(data).hexdigest(), len(data)))

    headers = {"Authorization": f"Bearer {token()}",
               "X-HereNow-Account": org,
               "Content-Type": "application/json"}
    body = {"files": [
        {"path": n, "size": sz, "contentType": ct, "hash": h}
        for n, ct, _, h, sz in file_specs
    ]}
    upd = api("PUT", f"/api/v1/publish/{slug}", body, extra=ws_headers)
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

    # Finalize: org context first (org-owned site); on 403 retry with bare auth.
    body = json.dumps({"versionId": version_id}).encode()
    fin_attempts = [
        {"Authorization": f"Bearer {token()}", "X-HereNow-Account": org,
         "Content-Type": "application/json"},
        {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
    ]
    for attempt in range(5):
        try:
            with req("POST", upload["finalizeUrl"], headers=fin_attempts[0], data=body,
                     timeout=120) as resp:
                fin = json.loads(resp.read().decode())
            print(f"finalized: {json.dumps(fin)}")
            return
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt == 0:
                print("finalize 403 with org header; retrying without it")
                with req("POST", upload["finalizeUrl"], headers=fin_attempts[1], data=body,
                         timeout=120) as resp:
                    fin = json.loads(resp.read().decode())
                print(f"finalized: {json.dumps(fin)}")
                return
            print(f"finalize attempt {attempt + 1} failed: {e}; retrying in 20s")
            time.sleep(20)
        except Exception as e:  # noqa: BLE001 - finalize timeouts are known-flaky
            print(f"finalize attempt {attempt + 1} failed: {e}; retrying in 20s")
            time.sleep(20)
    sys.exit("finalize failed after retries — check dashboard before re-running")


if __name__ == "__main__":
    main()
