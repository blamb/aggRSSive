"""Watching pages that have no feed.

Two ways to turn a plain web page into a source:

- **page** (new links): the page is read as a list. Every link that looks like an article (a decent amount of
  link text, not navigation) becomes an item the first time it is seen. Right for a news page, a "latest
  publications" page, an events listing.
- **pagediff** (changes): the page's main text is kept; when it changes, one item records what was added.
  Right for a policy page, a syllabus, a call for papers.

Both are polled on the normal schedule and produce ordinary items.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Item, Source, utcnow
from .http import client

PAGE_KINDS = {"page": "watched page: new links", "pagediff": "watched page: changes"}
NOISE = ("nav", "header", "footer", "aside", "script", "style", "noscript", "form", "svg")
NOISE_CLASS = re.compile(r"\b(nav|menu|footer|header|sidebar|cookie|breadcrumb|share|social|comment)s?\b", re.I)


def _main(soup: BeautifulSoup) -> BeautifulSoup:
    for t in soup.find_all(NOISE):
        t.decompose()
    for t in soup.find_all(attrs={"class": NOISE_CLASS}):
        t.decompose()
    for t in soup.find_all(attrs={"id": NOISE_CLASS}):
        t.decompose()
    return soup.find("main") or soup.find("article") or soup.body or soup


def page_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    return soup.title.string.strip() if soup.title and soup.title.string else ""


def link_entries(html: str, url: str, min_text: int = 15, limit: int = 100) -> list[dict]:
    """Article-like links on the page, in page order: [{"url", "title", "excerpt"}]."""
    soup = BeautifulSoup(html, "html.parser")
    root = _main(soup)
    page_host = urlparse(url).netloc
    seen: set[str] = set()
    out: list[dict] = []
    for a in root.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        full = urljoin(url, href).split("#")[0]
        p = urlparse(full)
        if p.scheme not in ("http", "https") or full.rstrip("/") == url.rstrip("/") or full in seen:
            continue
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if len(text) < min_text or p.netloc != page_host and len(text) < min_text * 2:
            continue
        seen.add(full)
        block = a.find_parent(("li", "article", "div", "p", "tr", "section")) or a
        excerpt = re.sub(r"\s+", " ", block.get_text(" ", strip=True))
        if excerpt.startswith(text):
            excerpt = excerpt[len(text):].strip(" -–—:|·")
        out.append({"url": full, "title": text[:300], "excerpt": excerpt[:300] if excerpt != text else ""})
        if len(out) >= limit:
            break
    return out


def main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    root = _main(soup)
    text = root.get_text("\n", strip=True)
    return re.sub(r"[ \t]+", " ", text)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 2]


def change_summary(old: str, new: str, limit: int = 6) -> tuple[list[str], list[str]]:
    """(added, removed) sentences between two snapshots of a page's text."""
    a, b = _sentences(old), _sentences(new)
    added, removed = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag in ("insert", "replace"):
            added.extend(b[j1:j2])
        if tag in ("delete", "replace"):
            removed.extend(a[i1:i2])
    return added[:limit], removed[:limit]


def _digest(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def fetch_page(db: Session, source: Source, fetch=None) -> int:
    """Poll a watched page; returns the number of new items. Mirrors fetch_source's bookkeeping."""
    source.last_fetched_at = utcnow()
    try:
        if fetch:
            html, final_url = fetch(source.feed_url)
        else:
            with client() as c:
                r = c.get(source.feed_url, headers={"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"})
            r.raise_for_status()
            html, final_url = r.text, str(r.url)
    except (httpx.HTTPError, ValueError) as e:
        source.last_error = str(e)[:1000]
        source.error_count += 1
        db.commit()
        return 0

    soup = BeautifulSoup(html, "html.parser")
    if not source.title:
        source.title = page_title(soup)[:500]
    if not source.site_url:
        source.site_url = final_url
    new = 0
    if source.kind == "page":
        existing = {g for (g,) in db.execute(select(Item.guid).where(Item.source_id == source.id))}
        for link in link_entries(html, final_url):
            if link["url"] in existing:
                continue
            existing.add(link["url"])
            db.add(Item(source_id=source.id, guid=link["url"][:2048], url=link["url"][:2048], title=link["title"][:1000], summary=f"<p>{_esc(link['excerpt'])}</p>" if link["excerpt"] else "", text=(link["title"] + " " + link["excerpt"]).strip()[:20000], published_at=utcnow()))
            new += 1
    else:  # pagediff
        text = main_text(html)
        digest = _digest(text)
        if source.snapshot is None:
            source.snapshot = text  # first look: remember, don't report
        elif _digest(source.snapshot) != digest:
            added, removed = change_summary(source.snapshot, text)
            parts = []
            if added:
                parts.append("<p><strong>Added:</strong></p><ul>" + "".join(f"<li>{_esc(s[:300])}</li>" for s in added) + "</ul>")
            if removed:
                parts.append("<p><strong>Removed:</strong></p><ul>" + "".join(f"<li>{_esc(s[:300])}</li>" for s in removed) + "</ul>")
            when = utcnow()
            db.add(Item(source_id=source.id, guid=f"{final_url}#{digest}"[:2048], url=final_url[:2048], title=f"{source.title or final_url}: changed {when:%b %-d}"[:1000], summary="".join(parts) or "<p>The page changed.</p>", text=" ".join(added + removed)[:20000] or "The page changed.", published_at=when))
            source.snapshot = text
            new += 1
    source.last_success_at = utcnow()
    source.last_error = None
    source.error_count = 0
    db.commit()
    return new


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
