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
    seen: dict[str, OpmlEntry] = {}

    def walk(node, path: list[str]):
        for outline in node.findall("outline"):
            xml_url = outline.get("xmlUrl")
            text = outline.get("title") or outline.get("text") or ""
            if xml_url:
                if xml_url in seen:
                    # Same feed listed under several folders: collect all of them as tags.
                    seen[xml_url].folders += [f for f in path if f not in seen[xml_url].folders]
                else:
                    seen[xml_url] = OpmlEntry(feed_url=xml_url, title=text, site_url=outline.get("htmlUrl"), folders=list(path))
                    out.append(seen[xml_url])
            else:
                walk(outline, path + [text] if text else path)

    walk(body, [])
    return out


def _attrs(e: OpmlEntry) -> str:
    q = {'"': "&quot;"}
    a = f'type="rss" text="{escape(e.title, q)}" title="{escape(e.title, q)}" xmlUrl="{escape(e.feed_url, q)}"'
    if e.site_url:
        a += f' htmlUrl="{escape(e.site_url, q)}"'
    return a


def render_opml(title: str, entries: list[OpmlEntry], by_folder: bool = False) -> str:
    """Render entries; with by_folder, each feed is listed under every one of its folders (tags)."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        f"  <head><title>{escape(title)}</title></head>",
        "  <body>",
    ]
    if by_folder:
        folders: dict[str, list[OpmlEntry]] = {}
        loose: list[OpmlEntry] = []
        for e in entries:
            for f in e.folders or []:
                folders.setdefault(f, []).append(e)
            if not e.folders:
                loose.append(e)
        for name in sorted(folders):
            lines.append(f'    <outline text="{escape(name, {chr(34): "&quot;"})}">')
            lines += [f"      <outline {_attrs(e)}/>" for e in folders[name]]
            lines.append("    </outline>")
        entries = loose
    lines += [f"    <outline {_attrs(e)}/>" for e in entries]
    lines += ["  </body>", "</opml>", ""]
    return "\n".join(lines)
