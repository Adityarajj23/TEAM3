"""Export approved pytest scripts from SQLite into a directory (used by CI).

Usage: python scripts/export_tests.py OUT_DIR [--project PAY]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db.base import session_scope  # noqa: E402
from app.db.models import Project, TestCase  # noqa: E402
from app.guardrails.ast_validator import validate_script  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--project")
a = ap.parse_args()
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
n = 0
with session_scope() as db:
    q = select(TestCase).where(TestCase.status == "approved", TestCase.automation == "pytest")
    if a.project:
        q = q.join(Project, Project.id == TestCase.project_id).where(Project.key == a.project)
    for t in db.execute(q).scalars():
        if not validate_script(t.script or "").valid:
            continue
        (out / ("test_" + t.key.replace("-", "_").lower() + ".py")).write_text(
            f"# TraceTest {t.key} v{t.version} sha256={t.script_hash}\n{t.script}")
        n += 1
print(f"exported {n} approved tests to {out}")
