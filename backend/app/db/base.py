"""SQLite engine, session factory and connection pragmas."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _configure_sqlite(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=10000")
    cur.close()


def make_engine(url: str | None = None) -> Engine:
    url = url or f"sqlite:///{get_settings().db_path}"
    eng = create_engine(url, connect_args={"check_same_thread": False, "timeout": 10}, pool_pre_ping=True)
    event.listen(eng, "connect", _configure_sqlite)
    return eng


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = make_engine()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine, _SessionLocal = None, None


def SessionLocal() -> Session:  # noqa: N802
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Short transaction: commit on success, rollback on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
