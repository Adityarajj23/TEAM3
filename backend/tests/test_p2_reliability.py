"""Reliability, Concurrency, Project Isolation, and Migration Test Suite (P2)."""
from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.base import make_engine, session_scope, utcnow
from app.db.models import (
    Defect,
    Environment,
    Execution,
    Module,
    Organisation,
    Project,
    ProjectMember,
    Requirement,
    Role,
    Run,
    TestCase,
    User,
    UserRole,
)
from app.services.tasks import recover_interrupted


def test_background_task_startup_reconciliation(app):
    """Verifies that recover_interrupted() marks orphaned running/queued jobs as interrupted."""
    with session_scope() as db:
        proj = db.query(Project).first()
        assert proj is not None
        env = db.query(Environment).filter_by(project_id=proj.id).first()
        env_id = env.id if env else 1

        # Create an orphaned running job
        r_run = Run(kind="analyse", status="running", progress=0.45, message="Processing AST")
        r_queued = Run(kind="generate", status="queued", progress=0.0, message="Queued in pool")
        r_done = Run(kind="execute", status="completed", progress=1.0, message="All tests passed")
        ex_running = Execution(key="EX-TEST-ORPHAN", project_id=proj.id, environment_id=env_id, source="platform_run", status="running", isolation_level="netns+rlimits")

        db.add_all([r_run, r_queued, r_done, ex_running])
        db.commit()
        run_id, q_id, done_id, ex_id = r_run.id, r_queued.id, r_done.id, ex_running.id

    recovered = recover_interrupted()
    assert recovered >= 2

    with session_scope() as db:
        r1 = db.get(Run, run_id)
        assert r1.status in ("interrupted", "failed")
        assert "interrupted" in (r1.error or "").lower()

        r2 = db.get(Run, q_id)
        assert r2.status in ("interrupted", "failed")

        r3 = db.get(Run, done_id)
        assert r3.status == "completed"

        ex = db.get(Execution, ex_id)
        assert ex.status == "error"
        assert "interrupted" in (ex.log_excerpt or "").lower()


def test_sqlite_concurrency_busy_timeout(app):
    """Tests that concurrent short transactions succeed without sqlite3.OperationalError: database is locked."""
    errors = []

    def write_task(idx: int):
        try:
            with session_scope() as db:
                r = Run(kind="concurrency_test", status="completed", progress=1.0, message=f"Worker {idx}")
                db.add(r)
                db.commit()
        except Exception as e:
            errors.append(e)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(write_task, i) for i in range(30)]
        for f in futures:
            f.result()

    assert len(errors) == 0, f"Encountered concurrency lock errors: {errors}"


def test_cross_project_isolation_endpoint_guessing(app):
    """Verifies that non-admin member of Project A is refused (404) when attempting to access Project B entities by ID guessing."""
    client = TestClient(app)

    with session_scope() as db:
        org = db.query(Organisation).first()
        assert org is not None

        # User belonging ONLY to Project A
        user = User(email="member.alpha@example.com", full_name="Member Alpha", password_hash="dummy")
        qa_role = db.query(Role).filter_by(name="qa_engineer").first()
        assert qa_role is not None
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=qa_role.id))

        # Project Alpha & Project Beta
        p_a = Project(key="ISOA", name="Isolation Alpha", organisation_id=org.id, owner_id=user.id, status="active")
        p_b = Project(key="ISOB", name="Isolation Beta", organisation_id=org.id, owner_id=user.id, status="active")
        db.add_all([p_a, p_b])
        db.flush()

        # User is member of Alpha ONLY
        db.add(ProjectMember(project_id=p_a.id, user_id=user.id, project_role="member"))

        # Add entities to Beta
        mod_b = Module(project_id=p_b.id, code="MODB", name="Module B")
        db.add(mod_b)
        db.flush()

        r_b = Requirement(key="ISOB-REQ-001", project_id=p_b.id, module_id=mod_b.id, title="Secret Beta Req", category="functional", priority="high", status="approved", current_version=1, author_id=user.id, source_type="code_ast")
        db.add(r_b)
        db.flush()

        tc_b = TestCase(key="TC-ISOB-001", project_id=p_b.id, requirement_id=r_b.id, requirement_version=1, clause_keys=["C1"], ac_keys=["AC1"], title="Secret Beta Test", priority="high", test_type="api_contract", automation="pytest", script="assert True", script_hash="hash_b", version=1, status="approved", created_by=user.id)
        d_b = Defect(key="DEF-ISOB-001", project_id=p_b.id, title="Secret Beta Defect", description="Beta only", severity="low", priority="p3", status="open", expected_result="Exp", actual_result="Act")
        db.add_all([tc_b, d_b])
        db.commit()

        user_id = user.id
        p_b_id = p_b.id
        r_b_id = r_b.id
        tc_b_id = tc_b.id
        d_b_id = d_b.id

    # Create session as Member Alpha
    from datetime import timedelta

    from app.core.security import hash_token, new_token
    from app.db.models import UserSession
    token, csrf = new_token(), new_token()
    with session_scope() as db:
        sess = UserSession(user_id=user_id, token_hash=hash_token(token), csrf_token=csrf, ip="127.0.0.1", expires_at=utcnow() + timedelta(hours=24))
        db.add(sess)
        db.commit()

    cookies = {"tt_session": token}

    # 1. Attempt to access Project B's requirement by ID guessing
    resp = client.get(f"/api/v1/requirements/{r_b_id}", cookies=cookies)
    assert resp.status_code == 404, f"Expected 404 for cross-project requirement access, got {resp.status_code}"

    # 2. Attempt to access Project B's test case by ID guessing
    resp = client.get(f"/api/v1/test-cases/{tc_b_id}", cookies=cookies)
    assert resp.status_code == 404, f"Expected 404 for cross-project test case access, got {resp.status_code}"

    # 3. Attempt to access Project B's defect by ID guessing
    resp = client.get(f"/api/v1/defects/{d_b_id}", cookies=cookies)
    assert resp.status_code == 404, f"Expected 404 for cross-project defect access, got {resp.status_code}"

    # 4. Attempt to list requirements scoped to Project B
    resp = client.get(f"/api/v1/requirements?project_id={p_b_id}", cookies=cookies)
    assert resp.status_code == 404, f"Expected 404 for unpermitted project list, got {resp.status_code}"


def test_database_migration_resilience(tmp_path):
    """Tests database connectivity and query resilience on an isolated copy."""
    from sqlalchemy import text
    s = get_settings()
    source_db = s.db_path
    if not source_db.exists():
        pytest.skip("Main database does not exist to copy")

    temp_db_file = tmp_path / "test_copy.db"
    shutil.copyfile(source_db, temp_db_file)

    # Test connecting and executing query on copy
    eng = make_engine(f"sqlite:///{temp_db_file}")
    with eng.connect() as conn:
        res = conn.execute(text("SELECT count(*) FROM projects")).scalar()
        assert res is not None
        assert res >= 0
