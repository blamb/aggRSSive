"""Hand-picked bookmarks: one page at a time, with its metadata pulled out for you.

A bookmark list is a Source of kind "bookmarks" that nothing polls; its items are added by hand. Pages are
described from what they say about themselves: Open Graph and Twitter cards, JSON-LD, standard meta tags,
and finally the title tag and first paragraph. Everything is a proposal the person can edit before saving.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .http import client

BOOKMARKS_KIND = "bookmarks"


@dataclass
class Extracted:
    url: str
    title: str = ""
    description: str = ""
    image_url: str | None = None
    author: str = ""
    published_at: datetime | None = None
    site_name: str = ""
    error: str | None = None


def _fetch(url: str) -> tuple[str, str]:
    with client() as c:
        r = c.get(url, headers={"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"})
        r.raise_for_status()
        return r.text, str(r.url)


def _date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.replace("Z", "+0000") if fmt.endswith("%z") else s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _jsonld(soup: BeautifulSoup) -> dict:
    """The first Article-like object in the page's JSON-LD, flattened to the fields we use."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        by_id = {}  # WordPress (Yoast, Rank Math) references the author Person by @id
        for node in list(stack) + (data.get("@graph", []) if isinstance(data, dict) else []):
            if isinstance(node, dict) and node.get("@id"):
                by_id[node["@id"]] = node
        while stack:
            node = stack.pop(0)
            if not isinstance(node, dict):
                continue
            if "@graph" in node:
                stack.extend(node["@graph"] if isinstance(node["@graph"], list) else [])
            t = node.get("@type", "")
            types = t if isinstance(t, list) else [t]
            if any(str(x).endswith(("Article", "BlogPosting", "NewsArticle", "WebPage", "VideoObject", "Report")) for x in types):
                author = node.get("author")
                if isinstance(author, list):
                    author = author[0] if author else None
                if isinstance(author, dict) and "@id" in author and "name" not in author:
                    author = by_id.get(author["@id"], author)
                name = author.get("name", "") if isinstance(author, dict) else (author or "")
                img = node.get("image")
                if isinstance(img, list):
                    img = img[0] if img else None
                if isinstance(img, dict):
                    img = img.get("url")
                return {"title": node.get("headline") or node.get("name") or "", "description": node.get("description") or "", "author": name, "published": node.get("datePublished"), "image": img}
    return {}


def parse_page(html: str, url: str) -> Extracted:
    soup = BeautifulSoup(html, "html.parser")

    def meta(*names: str) -> str:
        for n in names:
            tag = soup.find("meta", property=n) or soup.find("meta", attrs={"name": n})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return ""

    ld = _jsonld(soup)
    canonical = soup.find("link", rel="canonical")
    final = meta("og:url") or (canonical.get("href") if canonical else "") or url
    title = meta("og:title", "twitter:title") or ld.get("title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    site = meta("og:site_name")
    if site and title.endswith(f" - {site}") or title.endswith(f" | {site}"):
        title = title[: -(len(site) + 3)].rstrip()
    description = meta("og:description", "twitter:description", "description") or ld.get("description") or ""
    if not description:
        p = soup.find("p")
        description = p.get_text(" ", strip=True)[:300] if p else ""
    image = meta("og:image", "twitter:image") or ld.get("image") or ""
    author = meta("author", "article:author", "dc.creator") or ld.get("author") or ""
    if not author or author.startswith("http"):
        rel = soup.find("a", rel="author") or soup.find(attrs={"class": re.compile(r"\bauthor-name\b|\bbyline\b")})
        author = rel.get_text(" ", strip=True) if rel else ""
        if len(author) > 60 or author.lower().startswith("by ") and len(author) > 63:
            author = ""
    published = _date(meta("article:published_time", "date", "dc.date", "datePublished") or ld.get("published"))
    return Extracted(
        url=urljoin(url, final),
        title=re.sub(r"\s+", " ", title)[:500],
        description=re.sub(r"\s+", " ", description)[:1000],
        image_url=urljoin(url, image) if image else None,
        author=author[:255],
        published_at=published,
        site_name=site[:200],
    )


def extract(url: str, fetch=_fetch) -> Extracted:
    """Describe a page. Never raises: a page that can't be read comes back with `error` set and the URL kept."""
    try:
        html, final = fetch(url)
    except (httpx.HTTPError, ValueError) as e:
        return Extracted(url=url, error=f"Could not read the page ({e}). Fill in the details yourself.")
    try:
        return parse_page(html, final)
    except Exception as e:  # odd markup must not block a bookmark
        return Extracted(url=final, error=f"Could not make sense of the page ({e}).")
