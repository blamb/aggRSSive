"""Sessions, passwords, and the current-user dependency."""

from __future__ import annotations

import bcrypt
from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

COOKIE = "aggrssive_session"
MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="session")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def set_session(response, user: User) -> None:
    token = _serializer().dumps({"uid": user.id})
    secure = get_settings().base_url.startswith("https://")
    response.set_cookie(COOKIE, token, max_age=MAX_AGE, httponly=True, samesite="lax", secure=secure)


def clear_session(response) -> None:
    response.delete_cookie(COOKIE)


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=MAX_AGE)
    except BadSignature:
        return None
    u = db.get(User, data.get("uid"))
    return u if u and u.is_active else None


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def require_site_admin(user: User = Depends(require_user)) -> User:
    if not user.is_site_admin:
        raise HTTPException(status_code=403, detail="Site admins only")
    return user


def require_full_admin(user: User = Depends(require_user)) -> User:
    if not user.is_full_admin:
        raise HTTPException(status_code=403, detail="Full admins only")
    return user


def can_manage(user: User | None, owner_id: int | None) -> bool:
    """Owners and site admins may edit or delete a thing."""
    return user is not None and (user.is_site_admin or (owner_id is not None and user.id == owner_id))


def get_setting(db: Session, key: str, default: str = "") -> str:
    from .models import Setting

    row = db.get(Setting, key)
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    from .models import Setting

    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value
    db.commit()


def signup_open(db: Session) -> bool:
    v = get_setting(db, "allow_signup")
    return (v == "true") if v else get_settings().allow_signup
