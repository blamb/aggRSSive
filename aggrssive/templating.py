from datetime import datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from .config import get_settings

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
