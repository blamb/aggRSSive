"""One HTTP client for everything that fetches from the web."""

import httpx

from ..config import get_settings


def client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        headers={"User-Agent": s.user_agent, "Accept": "application/rss+xml, application/atom+xml, application/feed+json, application/json, text/xml, application/xml, text/html;q=0.8, */*;q=0.5"},
        timeout=s.fetch_timeout_seconds,
        follow_redirects=True,
        max_redirects=5,
    )
