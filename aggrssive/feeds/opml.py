"""OPML import and export."""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape


@dataclass
class OpmlEntry:
    feed_url: str
    title: str = ""
    site_url: str | None = None
    folders: list[str] = field(default_factory=list)  # nesting path, used as tag suggestions


def parse_opml(data: bytes) -> list[OpmlEntry]:
    root = ET.fromstring(data)
    body = root.find("body")
    if body is None:
        return []
    out: list[OpmlEntry] = []
    seen: set[str] = set()

    def walk(node, path: list[str]):
        for outline in node.findall("outline"):
            xml_url = outline.get("xmlUrl")
            text = outline.get("title") or outline.get("text") or ""
            if xml_url:
                if xml_url not in seen:
                    seen.add(xml_url)
                    out.append(OpmlEntry(feed_url=xml_url, title=text, site_url=outline.get("htmlUrl"), folders=list(path)))
            else:
                walk(outline, path + [text] if text else path)

    walk(body, [])
    return out


def render_opml(title: str, entries: list[OpmlEntry]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        f"  <head><title>{escape(title)}</title></head>",
        "  <body>",
    ]
    for e in entries:
        attrs = f'type="rss" text="{escape(e.title, {chr(34): "&quot;"})}" title="{escape(e.title, {chr(34): "&quot;"})}" xmlUrl="{escape(e.feed_url, {chr(34): "&quot;"})}"'
        if e.site_url:
            attrs += f' htmlUrl="{escape(e.site_url, {chr(34): "&quot;"})}"'
        lines.append(f"    <outline {attrs}/>")
    lines += ["  </body>", "</opml>", ""]
    return "\n".join(lines)
