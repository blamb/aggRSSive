from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import anonymous_open, clear_session, current_user, hash_password, set_session, signup_open, verify_password
from ..config import get_settings
from ..db import get_db
from ..models import OAuthAccount, User
from ..templating import templates

router = APIRouter()
settings = get_settings()

oauth = OAuth()
if settings.github_enabled:
    oauth.register(
        "github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )
if settings.google_enabled:
    oauth.register(
        "google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _safe_next(next_url: str | None) -> str:
    return next_url if next_url and next_url.startswith("/") and not next_url.startswith("//") else "/"


def _first_user_is_admin(db: Session) -> bool:
    return db.scalar(select(func.count(User.id))) == 0


@router.get("/login")
def login_page(request: Request, next: str = "/", user: User | None = Depends(current_user), db: Session = Depends(get_db)):
    if user:
        return RedirectResponse(_safe_next(next), status_code=303)
    return templates.TemplateResponse(request, "login.html", {"user": None, "next": next, "error": None, "anon_open": anonymous_open(db)})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form("/"), db: Session = Depends(get_db)):
    u = db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()
    if not u or not u.is_active or not verify_password(password, u.password_hash):
        return templates.TemplateResponse(request, "login.html", {"user": None, "next": next, "error": "Wrong email or password."}, status_code=400)
    resp = RedirectResponse(_safe_next(next), status_code=303)
    set_session(resp, u)
    return resp


@router.get("/signup")
def signup_page(request: Request, user: User | None = Depends(current_user), db: Session = Depends(get_db)):
    if user:
        return RedirectResponse("/", status_code=303)
    if not signup_open(db) and not _first_user_is_admin(db):
        raise HTTPException(403, "Sign-ups are closed here. Ask an admin for an account.")
    return templates.TemplateResponse(request, "signup.html", {"user": None, "error": None, "anon_open": anonymous_open(db)})


@router.post("/signup")
def signup(request: Request, email: str = Form(...), display_name: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    first = _first_user_is_admin(db)
    if not signup_open(db) and not first:
        raise HTTPException(403, "Sign-ups are closed here.")
    email = email.strip().lower()
    if len(password) < 8:
        return templates.TemplateResponse(request, "signup.html", {"user": None, "error": "Password needs at least 8 characters."}, status_code=400)
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        return templates.TemplateResponse(request, "signup.html", {"user": None, "error": "That email already has an account."}, status_code=400)
    u = User(email=email, display_name=display_name.strip()[:120] or email, password_hash=hash_password(password), is_admin=first, role="admin" if first else "user")
    db.add(u)
    db.commit()
    resp = RedirectResponse("/", status_code=303)
    set_session(resp, u)
    return resp


# --- Anonymous accounts: a secret link instead of an email and password -------------

_anon_recent: dict[str, list[float]] = {}  # ip -> creation times, to slow down bulk creation


def _anon_allowed(ip: str) -> bool:
    import time

    now = time.time()
    window = [t for t in _anon_recent.get(ip, []) if now - t < 3600]
    _anon_recent[ip] = window
    total = sum(len([t for t in v if now - t < 3600]) for v in _anon_recent.values())
    return len(window) < 5 and total < 40


@router.get("/anonymous")
def anonymous_page(request: Request, user: User | None = Depends(current_user), db: Session = Depends(get_db)):
    if user:
        return RedirectResponse("/account", status_code=303)
    if not anonymous_open(db):
        raise HTTPException(403, "Anonymous accounts are switched off here. Create an account with an email instead.")
    return templates.TemplateResponse(request, "anonymous.html", {"user": None, "error": None})


@router.post("/anonymous")
def anonymous_create(request: Request, acknowledge: bool = Form(False), db: Session = Depends(get_db)):
    if not anonymous_open(db):
        raise HTTPException(403, "Anonymous accounts are switched off here.")
    if not acknowledge:
        return templates.TemplateResponse(request, "anonymous.html", {"user": None, "error": "Tick the box to say you understand the terms."}, status_code=400)
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    if not _anon_allowed(ip):
        raise HTTPException(429, "Too many anonymous accounts created just now. Try again in an hour, or create an account with an email.")
    import secrets

    token = secrets.token_urlsafe(24)
    u = User(email=f"anon-{token[:12].lower()}@anonymous.invalid", display_name=f"Anonymous {token[:4]}", password_hash=None, role="user", is_anonymous=True, login_token=token)
    db.add(u)
    db.commit()
    resp = RedirectResponse("/account?m=welcome", status_code=303)
    set_session(resp, u)
    return resp


@router.get("/enter/{token}")
def anonymous_enter(token: str, db: Session = Depends(get_db)):
    """The secret link: signs the anonymous account in on this browser."""
    u = db.execute(select(User).where(User.login_token == token, User.is_anonymous.is_(True))).scalar_one_or_none()
    if not u or not u.is_active:
        raise HTTPException(404, "That link doesn't open an account any more. It may have been removed, or the account was claimed with an email.")
    resp = RedirectResponse("/", status_code=303)
    set_session(resp, u)
    return resp


@router.post("/account/claim")
def anonymous_claim(request: Request, email: str = Form(...), password: str = Form(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Turn an anonymous account into a regular one: same aggRSSives, now with an email and password."""
    if not user or not user.is_anonymous:
        raise HTTPException(400, "Only an anonymous account can be claimed.")
    email = email.strip().lower()
    if len(password) < 8:
        return RedirectResponse("/account?error=Password+needs+at+least+8+characters", status_code=303)
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        return RedirectResponse("/account?error=That+email+already+has+an+account", status_code=303)
    u = db.get(User, user.id)
    u.email, u.password_hash, u.is_anonymous, u.login_token = email, hash_password(password), False, None
    if u.display_name.startswith("Anonymous "):
        u.display_name = email.split("@")[0][:120]
    db.commit()
    return RedirectResponse("/account?m=claimed", status_code=303)


@router.post("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    clear_session(resp)
    return resp


# --- OAuth ---------------------------------------------------------------


@router.get("/auth/{provider}")
async def oauth_start(request: Request, provider: str):
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(404, f"{provider} sign-in is not configured.")
    redirect_uri = f"{settings.base_url}/auth/{provider}/callback"
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/auth/{provider}/callback")
async def oauth_callback(request: Request, provider: str, db: Session = Depends(get_db)):
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(404)
    token = await client.authorize_access_token(request)
    if provider == "github":
        profile = (await client.get("user", token=token)).json()
        pid = str(profile["id"])
        name = profile.get("name") or profile.get("login")
        email = profile.get("email")
        if not email:
            emails = (await client.get("user/emails", token=token)).json()
            primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
            email = primary["email"] if primary else None
    else:  # google
        info = token.get("userinfo") or {}
        pid = info.get("sub")
        name = info.get("name")
        email = info.get("email")
    if not email:
        raise HTTPException(400, "GitHub or Google did not share an email address, and aggRSSive needs one. Sign up with email instead.")
    email = email.lower()

    acct = db.execute(select(OAuthAccount).where(OAuthAccount.provider == provider, OAuthAccount.provider_user_id == pid)).scalar_one_or_none()
    if acct:
        u = acct.user
    else:
        u = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if u is None:
            if not signup_open(db) and not _first_user_is_admin(db):
                raise HTTPException(403, "Sign-ups are closed here.")
            first = _first_user_is_admin(db)
            u = User(email=email, display_name=(name or email)[:120], is_admin=first, role="admin" if first else "user")
            db.add(u)
            db.flush()
        db.add(OAuthAccount(user_id=u.id, provider=provider, provider_user_id=pid))
        db.commit()
    resp = RedirectResponse("/", status_code=303)
    set_session(resp, u)
    return resp
