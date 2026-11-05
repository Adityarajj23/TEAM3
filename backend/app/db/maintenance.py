"""Backup, restore, integrity checking and developer-only reset."""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.core.config import get_settings
from app.db.base import reset_engine, utcnow


def integrity_report(db_path: Path | None = None) -> dict:
    path = db_path or get_settings().db_path
    con = sqlite3.connect(str(path))
    try:
        quick = con.execute("PRAGMA integrity_check").fetchone()[0]
        fks = con.execute("PRAGMA foreign_key_check").fetchall()
        return {"integrity": quick, "foreign_key_violations": len(fks), "ok": quick == "ok" and not fks}
    finally:
        con.close()


def backup_database(dest: Path | None = None) -> Path:
    s = get_settings()
    dest = dest or s.backups_dir / f"tracetest-{utcnow().strftime('%Y%m%dT%H%M%S')}.db"
    src = sqlite3.connect(str(s.db_path))
    out = sqlite3.connect(str(dest))
    try:
        src.backup(out)  # online, consistent snapshot even in WAL mode
    finally:
        out.close()
        src.close()
    rep = integrity_report(dest)
    if not rep["ok"]:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Backup failed integrity check: {rep}")
    return dest


def restore_database(backup: Path) -> None:
    rep = integrity_report(backup)
    if not rep["ok"]:
        raise RuntimeError(f"Refusing to restore a corrupt backup: {rep}")
    s = get_settings()
    reset_engine()
    safety = s.backups_dir / f"pre-restore-{utcnow().strftime('%Y%m%dT%H%M%S')}.db"
    if s.db_path.exists():
        backup_database(safety)
    for suffix in ("-wal", "-shm"):
        Path(str(s.db_path) + suffix).unlink(missing_ok=True)
    shutil.copy2(backup, s.db_path)


def dev_reset() -> None:
    s = get_settings()
    if not s.is_dev:
        raise RuntimeError("Database reset is only available when TRACETEST_ENV=development or test")
    reset_engine()
    for p in (s.db_path, s.checkpoint_db_path):
        for suffix in ("", "-wal", "-shm"):
            Path(str(p) + suffix).unlink(missing_ok=True)
    shutil.rmtree(s.artifacts_dir, ignore_errors=True)
    s.artifacts_dir.mkdir(parents=True, exist_ok=True)
