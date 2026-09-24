"""LTI 1.3 mechanics: platform JWKS, id_token verification, deep-link responses, dynamic registration."""

from __future__ import annotations

import json
import secrets
import time
from datetime import timedelta
from urllib.parse import urlparse

import httpx
import jwt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import netfix
from ..config import get_settings
from ..models import LtiState, Platform, aware, utcnow
from . import keys

CLAIM = "https://purl.imsglobal.org/spec/lti/claim/"
DL_CLAIM = "https://purl.imsglobal.org/spec/lti-dl/claim/"
MSG_RESOURCE = "LtiResourceLinkRequest"
MSG_DEEPLINK = "LtiDeepLinkingRequest"
ROLE_INSTRUCTOR_MARKERS = ("#Instructor", "#Administrator", "#ContentDeveloper", "#TeachingAssistant")

STATE_TTL = timedelta(minutes=10)
_jwks_cache: dict[str, tuple[float, dict]] = {}


class LtiError(Exception):
    pass


def _request(method: str, url: str, **kw) -> httpx.Response:
    """HTTP to a platform, honouring DNS_OVERRIDES rewrites (see netfix.py)."""
    target, extra = netfix.rewrite(url)
    headers = {**extra, **(kw.pop("headers", None) or {})}
    return httpx.request(method, target, headers=headers, timeout=kw.pop("timeout", 20), follow_redirects=True, **kw)


# --- Platform keys ---------------------------------------------------------


def fetch_jwks(url: str) -> dict:
    now = time.time()
    hit = _jwks_cache.get(url)
    if hit and now - hit[0] < 3600:
        return hit[1]
    r = _request("GET", url, timeout=15)
    r.raise_for_status()
    data = r.json()
    _jwks_cache[url] = (now, data)
    return data


def _platform_key(platform: Platform, kid: str | None):
    jwks = fetch_jwks(platform.jwks_url)
    keys_ = jwks.get("keys", [])
    match = next((k for k in keys_ if kid is None or k.get("kid") == kid), None)
    if match is None:
        _jwks_cache.pop(platform.jwks_url, None)  # key may have rotated; refetch once
        keys_ = fetch_jwks(platform.jwks_url).get("keys", [])
        match = next((k for k in keys_ if kid is None or k.get("kid") == kid), None)
    if match is None:
        raise LtiError("Platform key not found in its JWKS")
    return jwt.PyJWK(match).key


# --- OIDC login -> launch ---------------------------------------------------


def find_platform(db: Session, issuer: str, client_id: str | None) -> Platform:
    q = select(Platform).where(Platform.issuer == issuer)
    if client_id:
        q = q.where(Platform.client_id == client_id)
    p = db.execute(q).scalars().first()
    if p is None:
        raise LtiError(f"Unknown platform: {issuer}. Register it first.")
    return p


def new_state(db: Session, platform: Platform) -> tuple[str, str]:
    db.execute(delete(LtiState).where(LtiState.created_at < utcnow() - STATE_TTL))
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(LtiState(state=state, nonce=nonce, platform_id=platform.id))
    db.commit()
    return state, nonce


def consume_state(db: Session, state: str) -> LtiState:
    s = db.get(LtiState, state)
    if s is None:
        raise LtiError("Launch state is missing or was already used. Please launch again from the course.")
    created = aware(s.created_at)
    db.delete(s)
    db.commit()
    if utcnow() - created > STATE_TTL:
        raise LtiError("Launch took too long. Please launch again from the course.")
    return s


def verify_launch(db: Session, platform: Platform, id_token: str, nonce: str) -> dict:
    header = jwt.get_unverified_header(id_token)
    key = _platform_key(platform, header.get("kid"))
    try:
        claims = jwt.decode(id_token, key, algorithms=["RS256"], audience=platform.client_id, issuer=platform.issuer, leeway=60)
    except jwt.PyJWTError as e:
        raise LtiError(f"Invalid launch token: {e}") from e
    if claims.get("nonce") != nonce:
        raise LtiError("Launch nonce mismatch")
    if claims.get(CLAIM + "version") != "1.3.0":
        raise LtiError("Only LTI 1.3 launches are supported")
    dep = claims.get(CLAIM + "deployment_id")
    if dep:
        known = platform.deployment_ids.split("\n") if platform.deployment_ids else []
        if dep not in known:
            platform.deployment_ids = "\n".join(known + [dep])
    platform.last_launch_at = utcnow()
    db.commit()
    return claims


def is_instructor(claims: dict) -> bool:
    return any(any(m in r for m in ROLE_INSTRUCTOR_MARKERS) for r in claims.get(CLAIM + "roles", []) or [])


# --- Tool-signed tokens -----------------------------------------------------


def sign(payload: dict, ttl_seconds: int = 300) -> str:
    now = int(time.time())
    body = {"iat": now, "exp": now + ttl_seconds, **payload}
    return jwt.encode(body, keys.private_pem(), algorithm="RS256", headers={"kid": keys.kid()})


def unsign(token: str, **kw) -> dict:
    try:
        return jwt.decode(token, keys.public_pem(), algorithms=["RS256"], **kw)
    except jwt.PyJWTError as e:
        raise LtiError(f"Invalid token: {e}") from e


def deep_link_response(platform: Platform, deployment_id: str, data: str | None, content_items: list[dict]) -> str:
    payload = {
        "iss": platform.client_id,
        "aud": [platform.issuer],
        "nonce": secrets.token_urlsafe(16),
        CLAIM + "message_type": "LtiDeepLinkingResponse",
        CLAIM + "version": "1.3.0",
        CLAIM + "deployment_id": deployment_id,
        DL_CLAIM + "content_items": content_items,
    }
    if data:
        payload[DL_CLAIM + "data"] = data
    return sign(payload, ttl_seconds=600)


def resource_link_item(base_url: str, title: str, slug: str, n: int, desc: str, img: bool, frame_height: int = 600) -> dict:
    return {
        "type": "ltiResourceLink",
        "title": title,
        "url": f"{base_url}/lti/launch",
        "custom": {"bundle": slug, "n": str(n), "desc": desc, "img": "1" if img else "0"},
        "iframe": {"height": frame_height},
    }


# --- Per-platform options ----------------------------------------------------
# Platform quirks and defaults live here, never as assumptions in the code paths.

OPTION_DEFAULTS = {
    "related": True,  # show "related posts" under each item in a launch
    "links_new_tab": True,  # open item links outside the platform's iframe
    "jwt_in_url": True,  # carry the Deep Linking JWT in the return URL as well as the POST body (Moodle needs it)
    "frame_height": 600,  # iframe height the platform is asked for
    "default_n": 10,  # items per launch when the resource link doesn't say
    "default_desc": "excerpt",  # excerpt | full | none
}


def platform_options(platform: Platform | None) -> dict:
    opts = dict(OPTION_DEFAULTS)
    if platform is not None and platform.options:
        try:
            saved = json.loads(platform.options)
        except ValueError:
            saved = {}
        for k in OPTION_DEFAULTS:
            if k in saved:
                opts[k] = saved[k]
    return opts


def set_platform_options(platform: Platform, form: dict) -> dict:
    """Coerce form values to the option types and store them. Unknown keys are ignored."""
    out = {}
    for k, default in OPTION_DEFAULTS.items():
        v = form.get(k)
        if isinstance(default, bool):
            out[k] = str(v).lower() in ("1", "true", "on", "yes")
        elif isinstance(default, int):
            try:
                out[k] = max(1, min(int(v), 2000))
            except (TypeError, ValueError):
                out[k] = default
        else:
            out[k] = v if v in ("excerpt", "full", "none") else default
    platform.options = json.dumps(out)
    return out


# --- Dynamic registration ---------------------------------------------------


def tool_configuration() -> dict:
    s = get_settings()
    base = s.base_url.rstrip("/")
    return {
        "application_type": "web",
        "response_types": ["id_token"],
        "grant_types": ["implicit", "client_credentials"],
        "initiate_login_uri": f"{base}/lti/login",
        "redirect_uris": [f"{base}/lti/launch"],
        "client_name": "aggRSSive",
        "jwks_uri": f"{base}/lti/jwks.json",
        "token_endpoint_auth_method": "private_key_jwt",
        "scope": "",
        "https://purl.imsglobal.org/spec/lti-tool-configuration": {
            "domain": urlparse(base).netloc,
            "description": "Live, curated lists of feeds and resources. Pick an aggRSSive and it stays up to date in your course.",
            "target_link_uri": f"{base}/lti/launch",
            "custom_parameters": {},
            "claims": ["iss", "sub", "name", "given_name", "family_name", "email"],
            "messages": [{"type": "LtiDeepLinkingRequest", "target_link_uri": f"{base}/lti/launch", "label": "aggRSSive"}],
        },
    }


def dynamic_register(db: Session, openid_configuration_url: str, registration_token: str | None) -> Platform:
    try:
        conf = _request("GET", openid_configuration_url)
        conf.raise_for_status()
    except httpx.HTTPError as e:
        host = urlparse(openid_configuration_url).netloc
        raise LtiError(
            f"Could not fetch the platform's configuration from {openid_configuration_url} ({e}). "
            f"The platform at '{host}' must be reachable from this server over the public internet; "
            "a Moodle on localhost, a private network or a Docker hostname cannot be registered from here."
        ) from e
    oc = conf.json()
    for k in ("issuer", "authorization_endpoint", "jwks_uri", "registration_endpoint"):
        if k not in oc:
            raise LtiError(f"Platform configuration is missing '{k}'")

    headers = {"Content-Type": "application/json"}
    if registration_token:
        headers["Authorization"] = f"Bearer {registration_token}"
    try:
        reg = _request("POST", oc["registration_endpoint"], json=tool_configuration(), headers=headers)
    except httpx.HTTPError as e:
        raise LtiError(f"Could not reach the platform's registration endpoint {oc['registration_endpoint']} ({e})") from e
    if reg.status_code >= 400:
        raise LtiError(f"Platform refused the registration ({reg.status_code}): {reg.text[:300]}")
    resp = reg.json()
    client_id = resp.get("client_id")
    if not client_id:
        raise LtiError("Platform did not return a client_id")

    pconf = oc.get("https://purl.imsglobal.org/spec/lti-platform-configuration", {})
    name = pconf.get("product_family_code", "") or urlparse(oc["issuer"]).netloc
    if pconf.get("version"):
        name = f"{name} {pconf['version']}"
    name = f"{name} ({urlparse(oc['issuer']).netloc})"
    tconf = resp.get("https://purl.imsglobal.org/spec/lti-tool-configuration", {})
    dep = tconf.get("deployment_id", "")

    existing = db.execute(select(Platform).where(Platform.issuer == oc["issuer"], Platform.client_id == client_id)).scalar_one_or_none()
    p = existing or Platform(issuer=oc["issuer"], client_id=client_id)
    p.name = name[:200]
    p.auth_login_url = oc["authorization_endpoint"]
    p.auth_token_url = oc.get("token_endpoint", "")
    p.jwks_url = oc["jwks_uri"]
    if dep and dep not in (p.deployment_ids or ""):
        p.deployment_ids = "\n".join([d for d in (p.deployment_ids or "").split("\n") if d] + [dep])
    db.add(p)
    db.commit()
    return p
