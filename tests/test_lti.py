"""LTI 1.3: OIDC login, deep-linking launch and response, resource launch, against a fake platform."""

import os
import tempfile
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/lti.db"
os.environ["SECRET_KEY"] = "test-key"
os.environ["LTI_KEY_PATH"] = f"{_dir}/lti.pem"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import scheduler  # noqa: E402
from aggrssive.config import get_settings  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.lti import keys, service  # noqa: E402
from aggrssive.lti.service import CLAIM, DL_CLAIM  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Bundle, Platform, Source, User  # noqa: E402

PLATFORM_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PLATFORM_PEM = PLATFORM_KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
ISS, CLIENT = "https://moodle.test", "client-123"
BASE = get_settings().base_url  # settings are process-wide and may already be cached by another test module


def platform_jwks():
    pub = PLATFORM_KEY.public_key()
    from aggrssive.lti.keys import _b64url

    n = pub.public_numbers()
    return {"keys": [{"kty": "RSA", "use": "sig", "alg": "RS256", "kid": "pk1", "n": _b64url(n.n, 256), "e": _b64url(n.e, 3)}]}


@pytest.fixture(scope="module")
def client():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    service.fetch_jwks = lambda url: platform_jwks()
    with SessionLocal() as db:
        u = User(email="o@example.edu", display_name="Owner", is_admin=True)
        db.add(u)
        db.flush()
        s = Source(feed_url="https://s.test/feed", title="S", added_by_id=u.id)
        db.add(s)
        db.flush()
        b = Bundle(owner_id=u.id, title="Picked Bundle", slug="picked1", is_public=True)
        b.sources.append(s)
        db.add(b)
        db.add(Platform(name="Test Moodle", issuer=ISS, client_id=CLIENT, auth_login_url="https://moodle.test/mod/lti/auth.php", jwks_url="https://moodle.test/certs", deployment_ids="dep-1"))
        db.commit()
    with TestClient(app) as c:
        yield c


def id_token(nonce, message_type, extra=None):
    now = int(time.time())
    claims = {
        "iss": ISS, "aud": CLIENT, "sub": "user-9", "name": "Pat Instructor", "iat": now, "exp": now + 300, "nonce": nonce,
        CLAIM + "message_type": message_type, CLAIM + "version": "1.3.0", CLAIM + "deployment_id": "dep-1",
        CLAIM + "roles": ["http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"],
        CLAIM + "target_link_uri": f"{BASE}/lti/launch",
    }
    claims.update(extra or {})
    return jwt.encode(claims, PLATFORM_PEM, algorithm="RS256", headers={"kid": "pk1"})


def start_login(client):
    r = client.get("/lti/login", params={"iss": ISS, "login_hint": "h", "target_link_uri": f"{BASE}/lti/launch", "client_id": CLIENT}, follow_redirects=False)
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["redirect_uri"] == [f"{BASE}/lti/launch"] and q["response_mode"] == ["form_post"]
    return q["state"][0], q["nonce"][0]


def test_jwks_served(client):
    j = client.get("/lti/jwks.json").json()
    assert j["keys"][0]["kid"] == keys.kid()


def test_deep_linking_round_trip(client):
    state, nonce = start_login(client)
    tok = id_token(nonce, service.MSG_DEEPLINK, {DL_CLAIM + "deep_linking_settings": {"deep_link_return_url": "https://moodle.test/return", "data": "opaque"}})
    r = client.post("/lti/launch", data={"id_token": tok, "state": state})
    assert r.status_code == 200 and "Picked Bundle" in r.text
    token = r.text.split('name="token" value="')[1].split('"')[0]

    r = client.post("/lti/deeplink", data={"token": token, "bundle": "picked1", "n": "5", "desc": "none", "img": "true"})
    assert r.status_code == 200 and 'action="https://moodle.test/return?JWT=' in r.text  # JWT also in the query string
    resp_jwt = r.text.split('name="JWT" value="')[1].split('"')[0]
    claims = jwt.decode(resp_jwt, keys.public_pem(), algorithms=["RS256"], audience=ISS)
    assert claims["iss"] == CLIENT and claims[CLAIM + "deployment_id"] == "dep-1" and claims[DL_CLAIM + "data"] == "opaque"
    item = claims[DL_CLAIM + "content_items"][0]
    assert item["type"] == "ltiResourceLink" and item["custom"] == {"bundle": "picked1", "n": "5", "desc": "none", "img": "1"}


def test_state_is_single_use(client):
    state, nonce = start_login(client)
    tok = id_token(nonce, service.MSG_RESOURCE, {CLAIM + "custom": {"bundle": "picked1"}})
    assert client.post("/lti/launch", data={"id_token": tok, "state": state}).status_code == 200
    r = client.post("/lti/launch", data={"id_token": tok, "state": state})
    assert r.status_code == 400 and "already used" in r.text


def test_resource_launch_renders_bundle_with_instructor_link(client):
    state, nonce = start_login(client)
    tok = id_token(nonce, service.MSG_RESOURCE, {CLAIM + "custom": {"bundle": "picked1", "n": "3", "desc": "none", "img": "0"}})
    r = client.post("/lti/launch", data={"id_token": tok, "state": state})
    assert r.status_code == 200
    assert "Picked Bundle" in r.text and "edit in aggRSSive" in r.text


def test_wrong_nonce_and_wrong_audience_rejected(client):
    state, nonce = start_login(client)
    r = client.post("/lti/launch", data={"id_token": id_token("other-nonce", service.MSG_RESOURCE), "state": state})
    assert r.status_code == 400 and "nonce" in r.text
    state, nonce = start_login(client)
    bad = id_token(nonce, service.MSG_RESOURCE, {"aud": "someone-else"})
    r = client.post("/lti/launch", data={"id_token": bad, "state": state})
    assert r.status_code == 400 and "Invalid launch token" in r.text


def test_unknown_platform(client):
    r = client.get("/lti/login", params={"iss": "https://stranger.test", "login_hint": "h", "target_link_uri": "x"})
    assert r.status_code == 400 and "Unknown platform" in r.text


def test_tool_configuration_shape():
    conf = service.tool_configuration()
    assert conf["initiate_login_uri"] == f"{BASE}/lti/login"
    assert conf["redirect_uris"] == [f"{BASE}/lti/launch"]
    lti = conf["https://purl.imsglobal.org/spec/lti-tool-configuration"]
    assert lti["domain"] == urlparse(BASE).netloc and lti["messages"][0]["type"] == "LtiDeepLinkingRequest"


def test_platform_options_change_launches(client):
    with SessionLocal() as db:
        pid = db.query(Platform).filter_by(issuer=ISS).one().id
        assert service.platform_options(db.get(Platform, pid))["related"] is True
    # Default launch: related posts on, links in a new tab.
    state, nonce = start_login(client)
    r = client.post("/lti/launch", data={"id_token": id_token(nonce, service.MSG_RESOURCE, {CLAIM + "custom": {"bundle": "picked1"}}), "state": state})
    assert "addEventListener('toggle'" in r.text and '<base target="_blank">' in r.text
    # A site admin turns them off and sets a frame height; the next launch and the next Deep Linking response follow.
    r = client.post(f"/lti/platforms/{pid}/options", data={"frame_height": "900", "default_n": "7", "default_desc": "none"}, follow_redirects=False)
    assert r.status_code in (303, 401, 403)  # 303 when the test client is signed in as a site admin
    with SessionLocal() as db:
        p = db.get(Platform, pid)
        service.set_platform_options(p, {"frame_height": "900", "default_n": "7", "default_desc": "none"})
        db.commit()
        o = service.platform_options(p)
        assert o == {"related": False, "links_new_tab": False, "jwt_in_url": False, "frame_height": 900, "default_n": 7, "default_desc": "none"}
    state, nonce = start_login(client)
    r = client.post("/lti/launch", data={"id_token": id_token(nonce, service.MSG_RESOURCE, {CLAIM + "custom": {"bundle": "picked1"}}), "state": state})
    assert "addEventListener('toggle'" not in r.text and "<base " not in r.text
    state, nonce = start_login(client)
    tok = id_token(nonce, service.MSG_DEEPLINK, {DL_CLAIM + "deep_linking_settings": {"deep_link_return_url": "https://moodle.test/return"}})
    r = client.post("/lti/launch", data={"id_token": tok, "state": state})
    assert 'name="n" value="7"' in r.text
    token = r.text.split('name="token" value="')[1].split('"')[0]
    r = client.post("/lti/deeplink", data={"token": token, "bundle": "picked1", "n": "5", "desc": "none"})
    assert 'action="https://moodle.test/return"' in r.text  # JWT no longer in the URL
    resp_jwt = r.text.split('name="JWT" value="')[1].split('"')[0]
    claims = jwt.decode(resp_jwt, keys.public_pem(), algorithms=["RS256"], audience=ISS)
    assert claims[DL_CLAIM + "content_items"][0]["iframe"]["height"] == 900
    with SessionLocal() as db:  # restore defaults for any later test
        p = db.get(Platform, pid)
        p.options = "{}"
        db.commit()
