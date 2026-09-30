#!/usr/bin/env python3
"""Generate feed.xml from the git history of index.html.

Each commit that adds or removes directory cards becomes one RSS item.
Pure formatting/copy commits (no net card changes) are skipped.
Run from the repo root:  python3 scripts/gen_feed.py
"""

import html
import re
import subprocess
import sys
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parent.parent
SITE_URL = "https://toolbox.rss.here.now"
MAX_ITEMS = 50

CARD_NAME = re.compile(
    r'<article class="card"[^>]*>.*?<h3><a href="[^"]*"[^>]*>([^<]+)</a></h3>'
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=True, capture_output=True, text=True,
    ).stdout


def side_names(diff_text: str, prefix: str) -> set[str]:
    names = set()
    for line in diff_text.splitlines():
        if not line.startswith(prefix):
            continue
        for m in CARD_NAME.finditer(line[1:]):
            names.add(html.unescape(m.group(1)).strip())
    return names


def main() -> None:
    log = git(
        "log", "--follow", "--format=%H%x1f%aI%x1f%s%x1e", "--", "index.html"
    )
    commits = []
    for chunk in log.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        h, date, subject = chunk.split("\x1f")
        commits.append((h.strip(), date.strip(), subject.strip()))

    items = []
    for i, (h, date, subject) in enumerate(commits):
        # Oldest commit (no parent): diff against the empty tree.
        parent = f"{h}^" if i < len(commits) - 1 else "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        diff = git("diff", "-U0", parent, h, "--", "index.html")
        added = side_names(diff, "+") - side_names(diff, "-")
        removed = side_names(diff, "-") - side_names(diff, "+")
        if not added and not removed:
            continue

        def names_phrase(names: set[str], verb: str) -> str:
            ordered = sorted(names)
            if len(ordered) > 5:
                return f"{verb} {len(ordered)} links"
            return f"{verb}: " + ", ".join(ordered)

        parts = []
        if added:
            parts.append(names_phrase(added, "Added"))
        if removed:
            parts.append(names_phrase(removed, "Removed"))
        title = "; ".join(parts) + "."

        desc_bits = [f"<p>{escape(p)}</p>" for p in parts]
        desc_bits.append(
            f'<p><a href="{SITE_URL}/">The RSS Universe</a> — {escape(subject)}</p>'
        )
        items.append(
            {
                "title": title,
                "link": f"{SITE_URL}/",
                "description": "".join(desc_bits),
                "date": datetime.fromisoformat(date),
                "guid": h,
            }
        )
        if len(items) >= MAX_ITEMS:
            break

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "<channel>",
        "<title>The RSS Universe — Changelog</title>",
        f"<link>{SITE_URL}/</link>",
        "<description>New apps, tools, and standards added to the RSS Universe directory.</description>",
        "<language>en</language>",
        f'<atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>',
    ]
    if items:
        lines.append(f"<lastBuildDate>{format_datetime(items[0]['date'])}</lastBuildDate>")
    for it in items:
        lines += [
            "<item>",
            f"<title>{escape(it['title'])}</title>",
            f"<link>{escape(it['link'])}</link>",
            f"<description>{escape(it['description'])}</description>",
            f"<pubDate>{format_datetime(it['date'])}</pubDate>",
            f'<guid isPermaLink="false">{it["guid"]}</guid>',
            "</item>",
        ]
    lines += ["</channel>", "</rss>"]

    out = REPO / "feed.xml"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} with {len(items)} items")


if __name__ == "__main__":
    sys.exit(main())
