"""Optional network overrides, for hosting quirks.

Some clouds (Jelastic/Virtuozzo, which Reclaim Cloud runs on) resolve the hostnames of *other*
environments on the same platform to their internal addresses, where HTTPS isn't served, and
block "hairpin" connections to the public load balancer. DNS_OVERRIDES handles both cases:

    DNS_OVERRIDES="lms.example.cloud=http://10.100.2.184"   # rewrite: talk plain HTTP to that
                                                            # address, keep the Host header
    DNS_OVERRIDES="lms.example.cloud=203.0.113.5"           # resolve: pin the name to an IP,
                                                            # TLS still validates the hostname

Several entries are separated by commas. The rewrite form stays on the private network; use it
only for addresses inside your own cloud.
"""

from __future__ import annotations

import logging
import socket
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger("aggrssive.netfix")
_resolve: dict[str, str] = {}
_rewrite: dict[str, str] = {}
_orig_getaddrinfo = socket.getaddrinfo


def parse(spec: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in spec.replace(";", ",").split(","):
        if "=" in pair:
            host, target = pair.split("=", 1)
            if host.strip() and target.strip():
                out[host.strip().lower()] = target.strip().rstrip("/")
    return out


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    ip = _resolve.get(str(host).lower()) if host else None
    if ip:
        return _orig_getaddrinfo(ip, port, family, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


def install(spec: str) -> dict[str, str]:
    global _resolve, _rewrite
    entries = parse(spec)
    _rewrite = {h: t for h, t in entries.items() if t.startswith(("http://", "https://"))}
    _resolve = {h: t for h, t in entries.items() if h not in _rewrite}
    if _resolve:
        socket.getaddrinfo = _patched_getaddrinfo
    if entries:
        log.info("network overrides active: %s", ", ".join(f"{h} -> {t}" for h, t in entries.items()))
    return entries


def rewrite(url: str) -> tuple[str, dict[str, str]]:
    """Return (url to actually request, extra headers). Identity for hosts without a rewrite."""
    parts = urlsplit(url)
    base = _rewrite.get(parts.hostname.lower()) if parts.hostname else None
    if not base:
        return url, {}
    b = urlsplit(base)
    return urlunsplit((b.scheme, b.netloc, parts.path, parts.query, parts.fragment)), {"Host": parts.netloc}
