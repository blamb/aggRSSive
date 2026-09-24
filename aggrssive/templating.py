from datetime import datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from .config import get_settings
from .feeds.adapters import ADAPTER_KINDS

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def ago(dt: datetime | None) -> str:
    if not dt:
        return "never"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    s = int(delta.total_seconds())
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    if s < 86400 * 30:
        return f"{s // 86400}d ago"
    return dt.strftime("%b %-d, %Y")


def datefmt(dt: datetime | None) -> str:
    return dt.strftime("%b %-d, %Y") if dt else ""


def safe(html: str) -> Markup:
    """Item HTML is sanitized at ingest; mark it safe for rendering."""
    return Markup(html or "")


templates.env.filters["ago"] = ago
templates.env.filters["datefmt"] = datefmt
templates.env.filters["safe_html"] = safe
templates.env.globals["settings"] = get_settings()


TAG_ORDERS = {"alpha": "alphabetical", "count": "most-used first"}


def order_tags(rows, user=None):
    """Sort (tag, count) rows for a tag cloud by the viewer's preference; alphabetical unless they chose otherwise."""
    pref = getattr(user, "tag_order", None) or "alpha"
    if pref == "count":
        return sorted(rows, key=lambda r: (-r[1], r[0].name))
    return sorted(rows, key=lambda r: r[0].name)


templates.env.globals["TAG_ORDERS"] = TAG_ORDERS


templates.env.globals["KIND_LABELS"] = ADAPTER_KINDS
