import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite:///"):
    path = settings.database_url.removeprefix("sqlite:///")
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from sqlalchemy import inspect, text

    from . import models  # noqa: F401  (registers tables)

    models.Base.metadata.create_all(engine)

    # Lightweight forward migration: add any column the models have that an older database lacks.
    # Good enough while the schema only ever grows; swap for Alembic if it ever needs more.
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in models.Base.metadata.sorted_tables:
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing:
                    ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col.type.compile(engine.dialect)}'
                    if col.default is not None and getattr(col.default, "is_scalar", False):
                        v = col.default.arg
                        ddl += " DEFAULT " + (f"'{v}'" if isinstance(v, str) else str(int(v) if isinstance(v, bool) else v))
                    conn.execute(text(ddl))
