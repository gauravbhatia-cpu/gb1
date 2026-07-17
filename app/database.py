import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings


def _runtime_database_url(configured_url: str) -> str:
    """Return a database URL that is writable in the current runtime.

    Vercel Functions ship the project directory as read-only. SQLite is only
    suitable there as a disposable demo database, so place it in the writable
    /tmp directory. A configured Postgres (or other server) URL is unchanged.
    """
    if os.getenv("VERCEL") and configured_url.startswith("sqlite"):
        database_name = Path(make_url(configured_url).database or "social_intel.db").name
        return f"sqlite:////tmp/{database_name}"
    return configured_url


database_url = _runtime_database_url(settings.database_url)

# Ensure the parent directory exists for local relative SQLite databases.
if database_url.startswith("sqlite"):
    sqlite_path = make_url(database_url).database
    if sqlite_path and sqlite_path != ":memory:":
        parent = Path(sqlite_path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401  (ensures models are registered)
    Base.metadata.create_all(bind=engine)
