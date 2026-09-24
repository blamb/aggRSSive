"""Admin hub, user management (full admins) and site settings."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_setting, hash_password, require_full_admin, require_site_admin, require_user, set_setting, signup_open, verify_password
from ..config import get_settings
from ..db import get_db
from ..models import Bundle, Platform, Source, User
from ..templating import templates

router = APIRouter()
ROLES = ("user", "site_admin", "admin")


@router.get("/admin")
def hub(request: Request, db: Session = Depends(get_db), user: User = Depends(require_site_admin)):
    stats = {
        "users": db.scalar(select(func.count(User.id))),
        "sources": db.scalar(select(func.count(Source.id))),
        "bundles": db.scalar(select(func.count(Bundle.id))),
        "platforms": db.scalar(select(func.count(Platform.id))),
    }
    return templates.TemplateResponse(request, "admin.html", {"user": user, "stats": stats, "signup_open": signup_open(db), "ai": get_settings().ai_enabled})


@router.get("/admin/users")
def users(request: Request, db: Session = Depends(get_db), user: User = Depends(require_full_admin)):
    rows = db.execute(select(User).order_by(User.created_at)).scalars().all()
    return templates.TemplateResponse(request, "admin_users.html", {"user": user, "users": rows, "roles": ROLES, "error": request.query_params.get("error")})


@router.post("/admin/users")
def create_user(display_name: str = Form(...), email: str = Form(...), role: str = Form("user"), password: str = Form(...), user: User = Depends(require_full_admin), db: Session = Depends(get_db)):
    email = email.strip().lower()
    if role not in ROLES or len(password) < 8:
        return RedirectResponse("/admin/users?error=Role+must+be+valid+and+password+at+least+8+characters", status_code=303)
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        return RedirectResponse("/admin/users?error=That+email+already+has+an+account", status_code=303)
    db.add(User(email=email, display_name=display_name.strip()[:120] or email, password_hash=hash_password(password), role=role, is_admin=role == "admin"))
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/users/{user_id}")
def update_user(user_id: int, action: str = Form(...), role: str = Form("user"), user: User = Depends(require_full_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404)
    if target.id == user.id and action in ("deactivate", "role") and (action == "deactivate" or role != "admin"):
        return RedirectResponse("/admin/users?error=You+can%27t+demote+or+deactivate+yourself", status_code=303)
    if action == "role" and role in ROLES:
        target.role = role
        target.is_admin = role == "admin"
    elif action == "deactivate":
        target.is_active = False
    elif action == "activate":
        target.is_active = True
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/admin/settings")
def update_settings(allow_signup: bool = Form(False), user: User = Depends(require_full_admin), db: Session = Depends(get_db)):
    set_setting(db, "allow_signup", "true" if allow_signup else "false")
    return RedirectResponse("/admin", status_code=303)


COLLECTIONS = Path(__file__).parent.parent / "collections"


def _collections(db: Session):
    """Starter OPML files shipped with the app, with how much of each is already imported."""
    from ..feeds.opml import parse_opml

    have = {u for (u,) in db.execute(select(Source.feed_url))}
    out = []
    for path in sorted(COLLECTIONS.glob("*.opml")):
        entries = parse_opml(path.read_bytes())
        title = re.search(r"<title>(.*?)</title>", path.read_text(encoding="utf-8"))
        out.append({
            "slug": path.stem,
            "title": title.group(1) if title else path.stem,
            "entries": entries,
            "count": len(entries),
            "imported": sum(1 for e in entries if e.feed_url in have),
            "tags": sorted({f for e in entries for f in e.folders}),
        })
    return out


@router.get("/admin/collections")
def collections(request: Request, db: Session = Depends(get_db), user: User = Depends(require_site_admin)):
    return templates.TemplateResponse(request, "admin_collections.html", {"user": user, "collections": _collections(db), "message": request.query_params.get("m")})


@router.post("/admin/collections/{slug}/import")
def import_collection(slug: str, db: Session = Depends(get_db), user: User = Depends(require_site_admin)):
    from .sources import import_entries

    col = next((c for c in _collections(db) if c["slug"] == slug), None)
    if not col:
        raise HTTPException(404, "No such collection")
    created, seen = import_entries(db, col["entries"], user, use_folders=True)
    return RedirectResponse(f"/admin/collections?m={created}+new+feeds+added+({seen - created}+already+here);+tags+and+classification+applied", status_code=303)


# --- Everyone: own account -------------------------------------------------


@router.get("/account")
def account(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(request, "account.html", {"user": user, "message": request.query_params.get("m"), "error": request.query_params.get("error")})


@router.post("/account")
def update_account(display_name: str = Form(...), tag_order: str = Form("alpha"), current_password: str = Form(""), new_password: str = Form(""), user: User = Depends(require_user), db: Session = Depends(get_db)):
    u = db.get(User, user.id)
    u.display_name = display_name.strip()[:120] or u.display_name
    u.tag_order = tag_order if tag_order in ("alpha", "count") else "alpha"
    if new_password:
        if len(new_password) < 8:
            return RedirectResponse("/account?error=New+password+needs+at+least+8+characters", status_code=303)
        if u.password_hash and not verify_password(current_password, u.password_hash):
            return RedirectResponse("/account?error=Current+password+is+wrong", status_code=303)
        u.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse("/account?m=Saved", status_code=303)
