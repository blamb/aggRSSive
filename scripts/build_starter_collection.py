"""Verify the candidate feeds and write the starter collection OPML.

    .venv/bin/python scripts/build_starter_collection.py [candidates.txt] [output.opml] ["Collection title"]

Every candidate is discovered and fetched. It is kept only if a feed is found and its newest item is
less than two years old. Tags become OPML folders; classification keys go into the OPML 2.0
`category` attribute as "/lcc/LB,/isced/0111", which aggRSSive's importer understands.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aggrssive.feeds.discover import discover, normalize_url  # noqa: E402
from aggrssive.feeds.fetch import parse_body  # noqa: E402
from aggrssive.feeds.http import client  # noqa: E402

MAX_AGE = timedelta(days=730)


def load_candidates(path: Path):
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url, tags, cats = [p.strip() for p in line.split("|")]
        yield url, [t.strip() for t in tags.split(",") if t.strip()], [c.strip() for c in cats.split(",") if c.strip()]


def check(url: str):
    try:
        cands = discover(normalize_url(url))
    except Exception as e:
        return None, f"discover failed: {e}"
    if not cands:
        return None, "no feed found"
    # Prefer the first non-comments feed.
    cand = next((c for c in cands if "comment" not in c.url.lower()), cands[0])
    try:
        with client() as c:
            r = c.get(cand.url)
            r.raise_for_status()
        parsed = parse_body(r.content, r.headers.get("content-type", ""))
    except Exception as e:
        return None, f"fetch failed: {e}"
    dates = [e.published_at for e in parsed.entries if e.published_at]
    newest = max(dates) if dates else None
    if not parsed.entries:
        return None, "feed has no items"
    if newest and datetime.now(timezone.utc) - newest > MAX_AGE:
        return None, f"stale: newest item {newest.date()}"
    return {"feed_url": cand.url, "title": parsed.title or cand.title or url, "site_url": parsed.site_url or url, "newest": newest}, "ok"


def main(cand_path: Path, out_path: Path, title: str) -> None:
    items = list(load_candidates(cand_path))
    print(f"checking {len(items)} candidates…", flush=True)
    kept, dropped = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for (url, tags, cats), (info, why) in zip(items, pool.map(lambda x: check(x[0]), items)):
            if info:
                kept.append((info, tags, cats))
                print(f"  ok   {info['title'][:50]:50} {info['feed_url']}", flush=True)
            else:
                dropped.append((url, why))
                print(f"  drop {url}  ({why})", flush=True)

    q = lambda v: escape(v or "", {'"': "&quot;"})  # noqa: E731
    folders: dict[str, list] = {}
    for info, tags, cats in kept:
        for t in tags:
            folders.setdefault(t, []).append((info, cats))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        "  <head>",
        f"    <title>{escape(title)}</title>",
        f"    <dateCreated>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')}</dateCreated>",
        f"    <ownerName>aggRSSive</ownerName>",
        "  </head>",
        "  <body>",
    ]
    for name in sorted(folders):
        lines.append(f'    <outline text="{q(name)}">')
        for info, cats in folders[name]:
            cat_attr = ",".join("/" + c.replace(":", "/") for c in cats)
            lines.append(
                f'      <outline type="rss" text="{q(info["title"])}" title="{q(info["title"])}" xmlUrl="{q(info["feed_url"])}" htmlUrl="{q(info["site_url"])}" category="{q(cat_attr)}"/>'
            )
        lines.append("    </outline>")
    lines += ["  </body>", "</opml>", ""]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nkept {len(kept)}, dropped {len(dropped)} -> {out_path}")
    for url, why in dropped:
        print(f"  dropped: {url}: {why}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    cand = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "scripts" / "starter_candidates.txt"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "aggrssive" / "collections" / "open-education.opml"
    title = sys.argv[3] if len(sys.argv) > 3 else "aggRSSive starter collection: open education, teaching and learning"
    main(cand, out, title)
