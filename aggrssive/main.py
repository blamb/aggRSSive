import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import scheduler
from .config import get_settings
from .db import init_db
from .routes import auth_routes, bundles, outputs, pages, sources, tags
from .templating import templates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

HERE = Path(__file__).parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="aggRSSive", version="2.0", lifespan=lifespan, docs_url=None, redoc_url=None)
# Only used by the OAuth dance (state/nonce); login itself uses a signed cookie in auth.py.
app.add_middleware(SessionMiddleware, secret_key=get_settings().secret_key, session_cookie="aggrssive_oauth", max_age=600, same_site="lax")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

app.include_router(pages.router)
app.include_router(auth_routes.router)
app.include_router(sources.router)
app.include_router(tags.router)
app.include_router(bundles.router)
app.include_router(outputs.router)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        return RedirectResponse(f"/login?next={request.url.path}", status_code=303)
    accepts_html = "text/html" in request.headers.get("accept", "")
    if accepts_html:
        return templates.TemplateResponse(request, "error.html", {"status": exc.status_code, "detail": exc.detail}, status_code=exc.status_code)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)


settings = get_settings()
if settings.secret_key == "dev-only-insecure-key":
    logging.getLogger("aggrssive").warning("SECRET_KEY is the insecure default. Set one in .env before exposing this to the internet.")
