"""Feed autodiscovery: give it any URL, get back feed URLs.

Order of attempts:
1. The URL itself is a feed (RSS, Atom or JSON Feed).
2. The page links to feeds via <link rel="alternate">.
3. Common well-known paths on the same site.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from .http import client

FEED_TYPES = {
    "application/rss+xml",
    "application/atom+xml",
    "application/feed+json",
    "application/json",
    "application/rdf+xml",
    "text/xml",
    "application/xml",
}

COMMON_PATHS = ["/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml", "/feed.xml", "/index.xml", "/feed.json", "/?feed=rss2"]


@dataclass
class Candidate:
    url: str
    title: str = ""
    kind: str = "feed"  # rss | atom | json | feed


def normalize_url(url: str) -> str:
    url = url.strip()
    if not urlparse(url).scheme:
        url = "https://" + url
    return url


def looks_like_feed(body: bytes, content_type: str) -> tuple[bool, str, str]:
    """Return (is_feed, kind, title)."""
    ct = (content_type or "").split(";")[0].strip().lower()
    head = body[:2048].lstrip().lower()
    if ct in {"application/feed+json", "application/json"} or head.startswith(b"{"):
        try:
            import json

            data = json.loads(body)
            if isinstance(data, dict) and "items" in data and ("version" in data or "title" in data):
                return True, "json", str(data.get("title", ""))
        except Exception:
            pass
        return False, "", ""
    if b"<rss" in head or b"<feed" in head or b"<rdf:rdf" in head or ct in FEED_TYPES:
        parsed = feedparser.parse(body)
        if parsed.get("version") or parsed.entries:
            kind = "atom" if str(parsed.get("version", "")).startswith("atom") else "rss"
            return True, kind, parsed.feed.get("title", "")
    return False, "", ""


def discover(url: str) -> list[Candidate]:
    url = normalize_url(url)
    from .adapters import adapt  # platform pages first: their feeds are not advertised on the page

    a = adapt(url)
    if a:
        return [Candidate(url=a.url, title=a.title, kind=a.kind)]
    with client() as c:
        try:
            r = c.get(url)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise ValueError(f"Could not fetch {url}: {e}") from e

        is_feed, kind, title = looks_like_feed(r.content, r.headers.get("content-type", ""))
        if is_feed:
            return [Candidate(url=str(r.url), title=title, kind=kind)]

        found: list[Candidate] = []
        seen: set[str] = set()
        soup = BeautifulSoup(r.content, "html.parser")
        for link in soup.find_all("link", rel=lambda v: v and "alternate" in v):
            t = (link.get("type") or "").lower()
            href = link.get("href")
            if href and t in FEED_TYPES:
                full = urljoin(str(r.url), href)
                if full not in seen:
                    seen.add(full)
                    found.append(Candidate(url=full, title=link.get("title") or "", kind="feed"))
        if found:
            return found

        base = f"{urlparse(str(r.url)).scheme}://{urlparse(str(r.url)).netloc}"
        for path in COMMON_PATHS:
            probe = base + path
            try:
                pr = c.get(probe)
                if pr.status_code == 200:
                    ok, kind, title = looks_like_feed(pr.content, pr.headers.get("content-type", ""))
                    if ok and str(pr.url) not in seen:
                        seen.add(str(pr.url))
                        found.append(Candidate(url=str(pr.url), title=title, kind=kind))
                        break
            except httpx.HTTPError:
                continue
        return found
