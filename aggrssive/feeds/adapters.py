"""Platform adapters: turn a profile, channel, library or search page into the feed that platform quietly serves.

Each adapter is a pure URL rewrite where possible (Mastodon, Bluesky, Hypothesis, Zotero groups) and a small page
fetch where the platform hides the ID (YouTube handles, Zotero user profiles). Adapters run before generic feed
discovery, so pasting https://bsky.app/profile/someone just works. Everything comes back as ordinary RSS/Atom,
so items from these platforms behave like any other: taggable, bundleable, filterable, embeddable, LTI-launchable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx

from .http import client


@dataclass
class Adapted:
    url: str  # the feed URL
    title: str
    kind: str  # youtube | mastodon | bluesky | zotero | hypothesis


ADAPTER_KINDS = {
    "podcast": "Podcast",
    "youtube": "YouTube",
    "mastodon": "Mastodon",
    "bluesky": "Bluesky",
    "zotero": "Zotero",
    "hypothesis": "Hypothesis",
}


def _fetch_text(url: str) -> str:
    with client() as c:
        r = c.get(url, headers={"Accept": "text/html"})
        r.raise_for_status()
        return r.text


# --- Podcast directories ----------------------------------------------------
# Apple's catalogue is the one directory that hands back the show's own feed, and its search needs no key.


class NoFeedHere(ValueError):
    """The page is a real thing but can never yield a feed; the message says what to do instead."""


def _fetch_json(url: str) -> dict:
    with client() as c:
        r = c.get(url, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()


def apple_podcasts(url: str, fetch_json=_fetch_json) -> Adapted | None:
    u = urlparse(url)
    if u.netloc.lower() not in ("podcasts.apple.com", "itunes.apple.com"):
        return None
    m = re.search(r"/id(\d+)", u.path)
    if not m:
        return None
    try:
        data = fetch_json(f"https://itunes.apple.com/lookup?id={m.group(1)}&entity=podcast")
    except httpx.HTTPError:
        return None
    for r in data.get("results", []):
        if r.get("feedUrl"):
            return Adapted(r["feedUrl"], r.get("collectionName") or "Podcast", "podcast")
    return None


def spotify(url: str) -> Adapted | None:
    u = urlparse(url)
    if u.netloc.lower().endswith("spotify.com") and "/show/" in u.path:
        raise NoFeedHere("Spotify pages don't carry a feed, and Spotify-only shows have none. Most shows also live in Apple Podcasts: paste the show's Apple Podcasts address, or search for it by name below.")
    return None


def search_podcasts(term: str, limit: int = 12, fetch_json=_fetch_json) -> list[dict]:
    """Shows matching a name or subject, each with its feed: [{"title", "author", "feed_url", "site_url", "image", "genres"}]."""
    from urllib.parse import quote

    term = term.strip()
    if not term:
        return []
    try:
        data = fetch_json(f"https://itunes.apple.com/search?media=podcast&entity=podcast&limit={min(limit, 25)}&term={quote(term)}")
    except (httpx.HTTPError, ValueError):
        return []
    out = []
    for r in data.get("results", []):
        if r.get("feedUrl"):
            out.append({"title": r.get("collectionName", ""), "author": r.get("artistName", ""), "feed_url": r["feedUrl"], "site_url": r.get("collectionViewUrl"), "image": r.get("artworkUrl100"), "genres": [g for g in r.get("genres", []) if g != "Podcasts"][:3]})
    return out


# --- YouTube ---------------------------------------------------------------


def youtube(url: str, fetch=_fetch_text) -> Adapted | None:
    u = urlparse(url)
    host = u.netloc.lower().removeprefix("www.").removeprefix("m.")
    if host not in ("youtube.com", "youtu.be"):
        return None
    q = parse_qs(u.query)
    if u.path in ("/feeds/videos.xml",):
        return None  # already a feed
    if u.path == "/playlist" and q.get("list"):
        pid = q["list"][0]
        return Adapted(f"https://www.youtube.com/feeds/videos.xml?playlist_id={pid}", "YouTube playlist", "youtube")
    m = re.match(r"^/channel/(UC[\w-]{20,})", u.path)
    if m:
        return Adapted(f"https://www.youtube.com/feeds/videos.xml?channel_id={m.group(1)}", "YouTube channel", "youtube")
    m = re.match(r"^/(@[\w.-]+|c/[\w.-]+|user/[\w.-]+)", u.path)
    if m:
        try:
            html = fetch(f"https://www.youtube.com/{m.group(1)}")
        except httpx.HTTPError:
            return None
        cid = re.search(r'<meta itemprop="identifier" content="(UC[\w-]+)"', html) or re.search(r'"channelId":"(UC[\w-]+)"', html) or re.search(r'youtube\.com/channel/(UC[\w-]+)', html)
        if not cid:
            return None
        t = re.search(r"<title>([^<]*)</title>", html)
        title = (t.group(1).replace(" - YouTube", "").strip() if t else "") or m.group(1)
        return Adapted(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid.group(1)}", title, "youtube")
    return None


# --- Mastodon (and anything speaking its URL conventions) ------------------


def mastodon(url: str) -> Adapted | None:
    u = urlparse(url)
    if u.path.endswith(".rss"):
        return None
    m = re.match(r"^/(@[\w.-]+)/?$", u.path)  # https://instance/@user
    if m and u.netloc:
        return Adapted(f"https://{u.netloc}/{m.group(1)}.rss", f"{m.group(1)}@{u.netloc}", "mastodon")
    m = re.match(r"^/users/([\w.-]+)/?$", u.path)  # https://instance/users/name
    if m and "hypothes.is" not in u.netloc:
        return Adapted(f"https://{u.netloc}/@{m.group(1)}.rss", f"@{m.group(1)}@{u.netloc}", "mastodon")
    m = re.match(r"^/tags/([\w-]+)/?$", u.path)  # https://instance/tags/topic
    if m:
        return Adapted(f"https://{u.netloc}/tags/{m.group(1)}.rss", f"#{m.group(1)} on {u.netloc}", "mastodon")
    return None


# --- Bluesky ---------------------------------------------------------------


def bluesky(url: str) -> Adapted | None:
    u = urlparse(url)
    if u.netloc.lower() not in ("bsky.app", "www.bsky.app"):
        return None
    m = re.match(r"^/profile/([^/]+)/?(rss)?$", u.path)
    if not m:
        return None
    return Adapted(f"https://bsky.app/profile/{m.group(1)}/rss", f"{m.group(1)} on Bluesky", "bluesky")


# --- Zotero ----------------------------------------------------------------

ZOTERO_QUERY = "format=atom&content=bib&limit=50&sort=dateAdded&direction=desc"


def zotero(url: str, fetch=_fetch_text) -> Adapted | None:
    u = urlparse(url)
    host = u.netloc.lower().removeprefix("www.")
    if host == "api.zotero.org":
        return None  # already an API URL; generic discovery handles it
    if host != "zotero.org":
        return None
    m = re.match(r"^/groups/(\d+)", u.path)
    if m:
        return Adapted(f"https://api.zotero.org/groups/{m.group(1)}/items/top?{ZOTERO_QUERY}", f"Zotero group {m.group(1)}", "zotero")
    m = re.match(r"^/users/(\d+)", u.path)
    if m:
        return Adapted(f"https://api.zotero.org/users/{m.group(1)}/items/top?{ZOTERO_QUERY}", f"Zotero library {m.group(1)}", "zotero")
    m = re.match(r"^/(groups/[\w-]+|[\w-]+)(/library)?/?$", u.path)
    if m:  # a group's name or a person's username: the page carries the numeric ID
        try:
            html = fetch(url)
        except httpx.HTTPError:
            return None
        t = re.search(r"<title>([^<]*)</title>", html)
        title = t.group(1).replace("Zotero | ", "").replace("People > ", "").replace("Groups > ", "").strip() if t else ""
        if u.path.startswith("/groups/"):
            gid = re.search(r'"id":(\d+)', html)
            return Adapted(f"https://api.zotero.org/groups/{gid.group(1)}/items/top?{ZOTERO_QUERY}", title or "Zotero group", "zotero") if gid else None
        uid = re.search(r'userID":(\d+)', html)
        if uid and uid.group(1) != "0":
            return Adapted(f"https://api.zotero.org/users/{uid.group(1)}/items/top?{ZOTERO_QUERY}", title or "Zotero library", "zotero")
    return None


# --- Hypothesis ------------------------------------------------------------


def hypothesis(url: str) -> Adapted | None:
    u = urlparse(url)
    if u.netloc.lower().removeprefix("www.") != "hypothes.is":
        return None
    if u.path.startswith("/stream.") or u.path.startswith("/api/"):
        return None
    m = re.match(r"^/users/([\w.-]+)", u.path)
    if m:
        return Adapted(f"https://hypothes.is/stream.atom?user={m.group(1)}", f"{m.group(1)}'s annotations", "hypothesis")
    m = re.match(r"^/groups/([\w-]+)", u.path)
    if m:
        return Adapted(f"https://hypothes.is/stream.atom?group={m.group(1)}", "Hypothesis group annotations", "hypothesis")
    q = parse_qs(u.query)
    if u.path in ("/search", "/search/") and q.get("q"):
        query = q["q"][0].strip()
        if query.startswith("tag:"):
            tag = query[4:].strip().strip("'\"")
            return Adapted(f"https://hypothes.is/stream.atom?tags={tag}", f"annotations tagged {tag}", "hypothesis")
        if query.startswith("user:"):
            user = query[5:].strip()
            return Adapted(f"https://hypothes.is/stream.atom?user={user}", f"{user}'s annotations", "hypothesis")
    return None


ADAPTERS = (apple_podcasts, spotify, youtube, mastodon, bluesky, zotero, hypothesis)


def adapt(url: str) -> Adapted | None:
    """The first adapter that recognises the URL wins. None means: use generic discovery.

    Raises NoFeedHere for pages that can never yield a feed, so the person gets told what to do instead.
    """
    for fn in ADAPTERS:
        try:
            a = fn(url)
        except NoFeedHere:
            raise
        except Exception:  # an adapter must never break discovery
            a = None
        if a:
            return a
    return None


def kind_for_feed_url(feed_url: str) -> str:
    """Which platform a feed URL belongs to, for labels and icons; 'feed' when it's just a feed."""
    host = urlparse(feed_url).netloc.lower()
    if "youtube.com" in host and "/feeds/videos.xml" in feed_url:
        return "youtube"
    if host == "bsky.app":
        return "bluesky"
    if host == "api.zotero.org":
        return "zotero"
    if "podcast" in feed_url.lower() or host in ("feeds.npr.org", "feeds.megaphone.fm", "feeds.simplecast.com", "anchor.fm", "feeds.buzzsprout.com", "feeds.transistor.fm", "feeds.libsyn.com", "rss.art19.com", "feeds.acast.com"):
        return "podcast"
    if host.endswith("hypothes.is"):
        return "hypothesis"
    if feed_url.endswith(".rss") and re.search(r"/(@[\w.-]+|tags/[\w-]+)\.rss$", feed_url):
        return "mastodon"
    return "feed"
