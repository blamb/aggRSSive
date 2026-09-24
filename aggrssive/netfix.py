"""Optional DNS overrides, for hosting quirks.

Some clouds (Jelastic/Virtuozzo, which Reclaim Cloud runs on) resolve the hostnames of *other*
environments on the same platform to their internal addresses, where HTTPS isn't served.
Set DNS_OVERRIDES="host=ip,host2=ip2" to pin those names to their public addresses so that
outbound calls (LTI registration, JWKS fetches, feed polling) go through the public load balancer.
Only name resolution changes; TLS still validates against the real hostname.
"""

from __future__ import annotations

import logging
import socket

log = logging.getLogger("aggrssive.netfix")
_overrides: dict[str, str] = {}
_orig_getaddrinfo = socket.getaddrinfo


def parse(spec: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in spec.replace(";", ",").split(","):
        if "=" in pair:
            host, ip = pair.split("=", 1)
            if host.strip() and ip.strip():
                out[host.strip().lower()] = ip.strip()
    return out


def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    ip = _overrides.get(str(host).lower()) if host else None
    if ip:
        return _orig_getaddrinfo(ip, port, family, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


def install(spec: str) -> dict[str, str]:
    global _overrides
    _overrides = parse(spec)
    if _overrides:
        socket.getaddrinfo = _patched_getaddrinfo
        log.info("DNS overrides active: %s", ", ".join(f"{h} -> {ip}" for h, ip in _overrides.items()))
    return _overrides
