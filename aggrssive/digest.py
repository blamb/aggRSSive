"""Email digests: new items from a bundle, daily or weekly, to people who asked.

Off until SMTP is configured (see config). A digest is sent only when there is something new since the last
one, so quiet lists stay quiet. Every mail carries a one-click unsubscribe link that needs no sign-in.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from html import escape

from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import get_settings
from .models import Bundle, Digest, User, aware, utcnow
from .rules import bundle_items

log = logging.getLogger("aggrssive.digest")

FREQUENCIES = {"daily": "every day", "weekly": "every week"}


def enabled() -> bool:
    return get_settings().mail_enabled


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().secret_key, salt="digest-unsubscribe")


def unsubscribe_token(d: Digest) -> str:
    return _serializer().dumps({"d": d.id, "u": d.user_id})


def digest_from_token(db: Session, token: str) -> Digest | None:
    try:
        data = _serializer().loads(token)
    except BadSignature:
        return None
    d = db.get(Digest, data.get("d"))
    return d if d and d.user_id == data.get("u") else None


def new_items(db: Session, d: Digest):
    """Items published since the last digest (or within one period, for a first digest)."""
    period = timedelta(days=7 if d.frequency == "weekly" else 1)
    since = aware(d.last_sent_at) or (utcnow() - period)
    items = bundle_items(db, d.bundle, limit=d.bundle.max_items)
    return [bi for bi in items if bi.pinned and not d.last_sent_at or (aware(bi.item.published_at) or utcnow()) > since]


def render(d: Digest, items, base_url: str) -> tuple[str, str, str]:
    """(subject, plain text, html)"""
    b = d.bundle
    n = len(items)
    subject = f"{b.title}: {n} new item{'s' if n != 1 else ''}"
    page = f"{base_url}/bundles/{b.slug}"
    unsub = f"{base_url}/digests/unsubscribe/{unsubscribe_token(d)}"
    lines = [f"{b.title}", f"{n} new item{'s' if n != 1 else ''} · {page}", ""]
    rows = []
    for bi in items:
        i = bi.item
        src = i.source.title or i.source.feed_url
        excerpt = (i.text[:240].rsplit(" ", 1)[0] + "…") if len(i.text) > 240 else i.text
        lines += [f"* {i.title}", f"  {src} · {i.url}"]
        if bi.note:
            lines.append(f"  Note: {bi.note}")
        if excerpt:
            lines.append(f"  {excerpt}")
        lines.append("")
        rows.append(
            f'<li style="margin:0 0 14px"><a href="{escape(i.url)}" style="font-weight:600;color:#0b5fa5;text-decoration:none">{escape(i.title or i.url)}</a>'
            f'<div style="color:#666;font-size:13px">{escape(src)}{" · " + escape(i.author) if i.author else ""}</div>'
            + (f'<div style="font-style:italic;color:#666;font-size:14px">{escape(bi.note)}</div>' if bi.note else "")
            + (f'<div style="font-size:14px;margin-top:2px">{escape(excerpt)}</div>' if excerpt else "")
            + "</li>"
        )
    lines += [f"You asked for this {FREQUENCIES[d.frequency]} on aggRSSive.", f"Unsubscribe: {unsub}"]
    html = (
        '<div style="font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1b1b1b;max-width:640px">'
        f'<h1 style="font-size:20px;border-bottom:2px solid #c8102e;padding-bottom:6px"><a href="{escape(page)}" style="color:#1b1b1b;text-decoration:none">{escape(b.title)}</a></h1>'
        f'<p style="color:#666">{n} new item{"s" if n != 1 else ""}</p><ul style="list-style:none;padding:0;margin:0">' + "".join(rows) + "</ul>"
        f'<p style="color:#888;font-size:12px;margin-top:24px">You asked for this {FREQUENCIES[d.frequency]} on aggRSSive. <a href="{escape(unsub)}" style="color:#888">Unsubscribe</a>.</p></div>'
    )
    return subject, "\n".join(lines), html


def send_mail(to: str, subject: str, text: str, html: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
        if s.smtp_starttls:
            smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)


def is_due(d: Digest, now: datetime) -> bool:
    hour = get_settings().digest_hour_utc
    last = aware(d.last_sent_at)
    if d.frequency == "weekly":
        return now.weekday() == 0 and now.hour == hour and (last is None or now - last > timedelta(days=6))
    return now.hour == hour and (last is None or now - last > timedelta(hours=20))


def run(db: Session, now: datetime | None = None, sender=send_mail) -> int:
    """Send every digest that is due and has something new. Returns how many were sent."""
    if not enabled():
        return 0
    now = now or datetime.now(timezone.utc)
    base = get_settings().base_url.rstrip("/")
    sent = 0
    for d in db.execute(select(Digest).options(selectinload(Digest.bundle), selectinload(Digest.user))).scalars().all():
        if not is_due(d, now) or not d.user.is_active or not d.user.email:
            continue
        if not d.bundle.is_public and d.bundle.owner_id != d.user_id:
            continue  # went private; nothing to say
        try:
            items = new_items(db, d)
            if items:
                subject, text, html = render(d, items, base)
                sender(d.user.email, subject, text, html)
                sent += 1
            d.last_sent_at = now  # a quiet period still counts as "checked"
            db.commit()
        except Exception:
            log.exception("digest failed for %s / %s", d.user.email, d.bundle.slug)
            db.rollback()
    return sent
