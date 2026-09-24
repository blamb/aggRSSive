from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import current_user, require_user
from ..config import get_settings
from ..db import get_db
from ..lti import keys, service
from ..lti.service import CLAIM, DL_CLAIM, LtiError
from ..models import Bundle, Platform, User
from ..rules import bundle_items
from ..templating import templates

router = APIRouter()
settings = get_settings()


def _err(request: Request, message: str, status: int = 400):
    return templates.TemplateResponse(request, "lti_error.html", {"message": message}, status_code=status)


# --- Public endpoints the platform talks to ---------------------------------


@router.get("/lti/jwks.json")
def jwks():
    return JSONResponse(keys.jwks(), headers={"Cache-Control": "public, max-age=3600"})


@router.api_route("/lti/login", methods=["GET", "POST"])
async def oidc_login(request: Request, db: Session = Depends(get_db)):
    params = dict(request.query_params)
    if request.method == "POST":
        params.update(dict(await request.form()))
    iss, login_hint, target = params.get("iss"), params.get("login_hint"), params.get("target_link_uri")
    if not (iss and login_hint and target):
        return _err(request, "This address is the LTI login endpoint; it only works when launched from a course.")
    try:
        platform = service.find_platform(db, iss, params.get("client_id"))
    except LtiError as e:
        return _err(request, str(e))
    state, nonce = service.new_state(db, platform)
    q = {
        "scope": "openid",
        "response_type": "id_token",
        "response_mode": "form_post",
        "prompt": "none",
        "client_id": platform.client_id,
        "redirect_uri": f"{settings.base_url}/lti/launch",
        "login_hint": login_hint,
        "state": state,
        "nonce": nonce,
    }
    if params.get("lti_message_hint"):
        q["lti_message_hint"] = params["lti_message_hint"]
    sep = "&" if "?" in platform.auth_login_url else "?"
    return RedirectResponse(platform.auth_login_url + sep + urlencode(q), status_code=302)


@router.post("/lti/launch")
def launch(request: Request, id_token: str = Form(...), state: str = Form(...), db: Session = Depends(get_db)):
    try:
        st = service.consume_state(db, state)
        platform = db.get(Platform, st.platform_id)
        claims = service.verify_launch(db, platform, id_token, st.nonce)
    except LtiError as e:
        return _err(request, str(e))

    msg = claims.get(CLAIM + "message_type")
    if msg == service.MSG_DEEPLINK:
        return _picker(request, db, platform, claims)
    if msg == service.MSG_RESOURCE:
        return _resource(request, db, platform, claims)
    return _err(request, f"Unsupported LTI message type: {msg}")


def _picker(request: Request, db: Session, platform: Platform, claims: dict):
    dl = claims.get(DL_CLAIM + "deep_linking_settings", {})
    return_url = dl.get("deep_link_return_url")
    if not return_url:
        return _err(request, "The platform did not say where to return the selection.")
    token = service.sign(
        {
            "purpose": "deeplink",
            "platform_id": platform.id,
            "deployment_id": claims.get(CLAIM + "deployment_id", ""),
            "return_url": return_url,
            "data": dl.get("data"),
        },
        ttl_seconds=1800,
    )
    bundles = db.execute(select(Bundle).where(Bundle.is_public.is_(True)).options(selectinload(Bundle.owner), selectinload(Bundle.sources)).order_by(Bundle.title)).scalars().all()
    return templates.TemplateResponse(request, "lti_pick.html", {"bundles": bundles, "token": token, "platform": platform, "name": claims.get("name", "")})


@router.post("/lti/deeplink")
def deeplink_select(request: Request, token: str = Form(...), bundle: str = Form(...), n: int = Form(10), desc: str = Form("excerpt"), img: bool = Form(False), db: Session = Depends(get_db)):
    try:
        t = service.unsign(token)
        if t.get("purpose") != "deeplink":
            raise LtiError("Wrong token")
    except LtiError as e:
        return _err(request, str(e))
    platform = db.get(Platform, t["platform_id"])
    b = db.execute(select(Bundle).where(Bundle.slug == bundle, Bundle.is_public.is_(True))).scalar_one_or_none()
    if platform is None or b is None:
        return _err(request, "That aggRSSive is not available.", 404)
    if desc not in ("excerpt", "full", "none"):
        desc = "excerpt"
    item = service.resource_link_item(settings.base_url, b.title, b.slug, max(1, min(n, 100)), desc, img)
    jwt_ = service.deep_link_response(platform, t.get("deployment_id", ""), t.get("data"), [item])
    return templates.TemplateResponse(request, "lti_autopost.html", {"action": t["return_url"], "fields": {"JWT": jwt_}})


def _resource(request: Request, db: Session, platform: Platform, claims: dict):
    custom = claims.get(CLAIM + "custom", {}) or {}
    slug = custom.get("bundle")
    if not slug:
        # Fallback: a resource added with a plain URL like .../lti/launch?bundle=slug
        target = claims.get(CLAIM + "target_link_uri", "")
        if "bundle=" in target:
            slug = target.split("bundle=", 1)[1].split("&", 1)[0]
    b = db.execute(select(Bundle).where(Bundle.slug == slug).options(selectinload(Bundle.sources), selectinload(Bundle.overrides), selectinload(Bundle.owner))).scalar_one_or_none() if slug else None
    if b is None or not b.is_public:
        return _err(request, "This aggRSSive no longer exists or has been made private.", 404)
    try:
        n = max(1, min(int(custom.get("n", 10)), 100))
    except ValueError:
        n = 10
    desc = custom.get("desc", "excerpt")
    img = str(custom.get("img", "1")) == "1"
    items = bundle_items(db, b, limit=n)
    return templates.TemplateResponse(
        request,
        "lti_resource.html",
        {"bundle": b, "items": items, "desc": desc, "img": img, "instructor": service.is_instructor(claims), "base_url": settings.base_url},
    )


@router.get("/lti/register")
def register(request: Request, openid_configuration: str = "", registration_token: str = "", db: Session = Depends(get_db)):
    if not openid_configuration:
        return _err(request, "This is the dynamic registration URL. Paste it into your platform's 'register a tool' form rather than opening it directly.")
    try:
        p = service.dynamic_register(db, openid_configuration, registration_token or None)
    except (LtiError, ValueError) as e:
        return _err(request, f"Registration failed: {e}")
    except Exception as e:  # network errors etc.
        return _err(request, f"Registration failed: {e}")
    return templates.TemplateResponse(request, "lti_registered.html", {"platform": p})


# --- Admin ------------------------------------------------------------------


@router.get("/lti")
def admin(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    if not (user and user.is_admin):
        raise HTTPException(403, "Admins only")
    platforms = db.execute(select(Platform).order_by(Platform.created_at.desc())).scalars().all()
    base = settings.base_url
    urls = {
        "Dynamic registration URL": f"{base}/lti/register",
        "Tool URL / target link": f"{base}/lti/launch",
        "Initiate login URL": f"{base}/lti/login",
        "Redirection URI": f"{base}/lti/launch",
        "Public keyset (JWKS)": f"{base}/lti/jwks.json",
        "Deep linking URL": f"{base}/lti/launch",
    }
    return templates.TemplateResponse(request, "lti_admin.html", {"user": user, "platforms": platforms, "urls": urls})


@router.post("/lti/platforms")
def add_platform(name: str = Form(""), issuer: str = Form(...), client_id: str = Form(...), auth_login_url: str = Form(...), auth_token_url: str = Form(""), jwks_url: str = Form(...), deployment_id: str = Form(""), user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(403)
    p = Platform(name=name.strip()[:200] or issuer, issuer=issuer.strip(), client_id=client_id.strip(), auth_login_url=auth_login_url.strip(), auth_token_url=auth_token_url.strip(), jwks_url=jwks_url.strip(), deployment_ids=deployment_id.strip())
    db.add(p)
    db.commit()
    return RedirectResponse("/lti", status_code=303)


@router.post("/lti/platforms/{platform_id}/delete")
def delete_platform(platform_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not user.is_admin:
        raise HTTPException(403)
    p = db.get(Platform, platform_id)
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/lti", status_code=303)
