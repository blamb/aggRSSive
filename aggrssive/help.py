"""In-app help, rendered from the Markdown files in aggrssive/docs/.

The docs ship with the code so they are versioned with it. Rule for contributors: a change that
alters what a person sees or does updates the relevant page in the same commit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import markdown
import nh3

DOCS = Path(__file__).parent / "docs"

ALLOWED_TAGS = {"a", "p", "br", "em", "strong", "code", "pre", "ul", "ol", "li", "blockquote", "h1", "h2", "h3", "h4", "table", "thead", "tbody", "tr", "th", "td", "hr", "img"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "img": {"src", "alt"}, "th": {"align"}, "td": {"align"}}


@dataclass
class Page:
    slug: str
    title: str
    order: int
    html: str


def _front_matter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, text[m.end():]


@lru_cache
def pages() -> dict[str, Page]:
    out: dict[str, Page] = {}
    for path in DOCS.glob("*.md"):
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        html = markdown.markdown(body, extensions=["tables", "fenced_code"])
        # Relative links between pages: "roles" -> "/help/roles".
        html = re.sub(r'href="([a-z0-9-]+)"', r'href="/help/\1"', html)
        html = nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
        slug = path.stem
        out[slug] = Page(slug=slug, title=meta.get("title", slug), order=int(meta.get("order", 99)), html=html)
    return dict(sorted(out.items(), key=lambda kv: kv[1].order))
