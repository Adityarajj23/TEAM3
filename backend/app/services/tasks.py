"""In-process background task system with persisted run records (SQLite) for progress/SSE."""
from __future__ import annotations

import logging
import threading
import traceback
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from app.db.base import session_scope, utcnow
from app.db.models import Run, RunStep

log = logging.getLogger("tracetest.tasks")
_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="tt-worker")
_futures: dict[int, Future] = {}
_lock = threading.Lock()
SYNC_MODE = False  # tests may run tasks inline for determinism


def create_run(kind: str, subject_type: str | None, subject_id: int | None, actor_id: int | None,
               message: str = "Queued") -> int:
    with session_scope() as db:
        r = Run(kind=kind, subject_type=subject_type, subject_id=subject_id, created_by=actor_id, message=message)
        db.add(r)
        db.flush()
        return r.id


def update_run(run_id: int, **fields) -> None:
    with session_scope() as db:
        r = db.get(Run, run_id)
        for k, v in fields.items():
            setattr(r, k, v)


def step(run_id: int, name: str, status: str = "completed", detail: dict | None = None,
         progress: float | None = None) -> None:
    with session_scope() as db:
        db.add(RunStep(run_id=run_id, name=name, status=status, detail=detail or {}, finished_at=utcnow()))
        r = db.get(Run, run_id)
        r.message = f"{name}: {status}"
        if progress is not None:
            r.progress = progress


def submit(run_id: int, fn: Callable[[int], dict | None]) -> None:
    def wrapper():
        update_run(run_id, status="running", started_at=utcnow())
        try:
            result = fn(run_id) or {}
            with session_scope() as db:
                r = db.get(Run, run_id)
                if r.status == "running":
                    r.status = result.pop("_status", "completed")
                    r.progress = 1.0 if r.status == "completed" else r.progress
                r.result = {**(r.result or {}), **result}
                if r.status in ("completed", "failed", "degraded"):
                    r.finished_at = utcnow()
        except Exception as exc:
            log.error("Run %s failed: %s", run_id, traceback.format_exc())
            update_run(run_id, status="failed", error=str(exc)[:4000], finished_at=utcnow(), message="Failed")
    if SYNC_MODE:
        wrapper()
        return
    with _lock:
        _futures[run_id] = _pool.submit(wrapper)


def recover_interrupted() -> int:
    """Runs left 'running' or 'queued' by a previous process are marked failed (workflow checkpoints persist)."""
    with session_scope() as db:
        rows = db.query(Run).filter(Run.status.in_(["running", "queued"])).all()
        for r in rows:
            r.status, r.error, r.finished_at = "failed", "Interrupted by application restart; retry the operation", utcnow()
        from app.db.models import Execution
        for ex in db.query(Execution).filter(Execution.status.in_(["running", "queued"])).all():
            ex.status, ex.log_excerpt = "error", "Interrupted by application restart"
        return len(rows)
