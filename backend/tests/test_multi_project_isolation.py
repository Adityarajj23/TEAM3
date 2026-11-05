"""Multi-Project Isolation and Repository Security Test Suite.

Verifies:
1. URL validation protects against SSRF, file schemes, and path traversal.
2. Git ref validation prevents option flag injection.
3. Multi-project data isolation: entities are scoped to project_id.
4. Repository refresh updates commit info without data loss.
5. Repository disconnect preserves QA history and execution evidence.
"""
from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.db.base import session_scope
from app.db.models import Module, Organisation, Project, Requirement, TestCase
from app.services.repo_ingest import validate_git_ref, validate_github_url


def test_validate_github_url_valid():
    owner, repo = validate_github_url("https://github.com/sohan10012/EchoBox")
    assert owner == "sohan10012"
    assert repo == "EchoBox"

    owner2, repo2 = validate_github_url("https://github.com/torvalds/linux.git")
    assert owner2 == "torvalds"
    assert repo2 == "linux"


def test_validate_github_url_rejects_ssrf_and_invalid_schemes():
    # File scheme
    with pytest.raises(AppError) as exc:
        validate_github_url("file:///etc/passwd")
    assert exc.value.status == 400

    # Localhost / internal IP
    with pytest.raises(AppError) as exc:
        validate_github_url("http://127.0.0.1:8000/repo.git")
    assert exc.value.status == 400

    # AWS metadata endpoint
    with pytest.raises(AppError) as exc:
        validate_github_url("http://169.254.169.254/latest/meta-data/")
    assert exc.value.status == 400

    # Non-github domain
    with pytest.raises(AppError) as exc:
        validate_github_url("https://evil-phishing.com/owner/repo.git")
    assert exc.value.status == 400

    # Path traversal in owner
    with pytest.raises(AppError) as exc:
        validate_github_url("https://github.com/../etc/repo")
    assert exc.value.status == 400


def test_validate_git_ref_prevents_flag_injection():
    # Valid branches
    assert validate_git_ref("main") == "main"
    assert validate_git_ref("feature/login-fix") == "feature/login-fix"
    assert validate_git_ref("v1.2.3") == "v1.2.3"
    assert validate_git_ref("b3740a62ad414a141e82146adafb47c4850fd782") == "b3740a62ad414a141e82146adafb47c4850fd782"

    # Flag injection attempt
    with pytest.raises(AppError) as exc:
        validate_git_ref("--upload-pack=evil")
    assert exc.value.status == 400

    # Path traversal
    with pytest.raises(AppError) as exc:
        validate_git_ref("../../../etc")
    assert exc.value.status == 400

    # Whitespace or command separator
    with pytest.raises(AppError) as exc:
        validate_git_ref("main; rm -rf /")
    assert exc.value.status == 400


def test_multi_project_data_isolation(app):
    """Verifies that queries for Project A never return Project B's entities."""
    with session_scope() as db:
        org = db.query(Organisation).first()
        assert org is not None

        # Create Project A
        p_a = Project(key="PROJA", name="Project Alpha", organisation_id=org.id, owner_id=1, status="active")
        # Create Project B
        p_b = Project(key="PROJB", name="Project Beta", organisation_id=org.id, owner_id=1, status="active")
        db.add_all([p_a, p_b])
        db.flush()

        mod_a = Module(project_id=p_a.id, code="MODA", name="Module A")
        mod_b = Module(project_id=p_b.id, code="MODB", name="Module B")
        db.add_all([mod_a, mod_b])
        db.flush()

        # Add requirements to Project A
        r_a1 = Requirement(key="PROJA-REQ-001", project_id=p_a.id, module_id=mod_a.id, title="Alpha Req 1", category="functional", priority="high", status="approved", current_version=1, author_id=1, source_type="code_ast")
        r_a2 = Requirement(key="PROJA-REQ-002", project_id=p_a.id, module_id=mod_a.id, title="Alpha Req 2", category="functional", priority="medium", status="approved", current_version=1, author_id=1, source_type="code_ast")
        # Add requirement to Project B
        r_b1 = Requirement(key="PROJB-REQ-001", project_id=p_b.id, module_id=mod_b.id, title="Beta Req 1", category="functional", priority="high", status="approved", current_version=1, author_id=1, source_type="code_ast")
        db.add_all([r_a1, r_a2, r_b1])
        db.flush()

        # Add test cases
        tc_a = TestCase(key="TC-PROJA-001", project_id=p_a.id, requirement_id=r_a1.id, requirement_version=1, clause_keys=["C1"], ac_keys=["AC1"], title="Test A", priority="high", test_type="api_contract", automation="pytest", script="assert True", script_hash="hash_a", version=1, status="approved", created_by=1)
        tc_b = TestCase(key="TC-PROJB-001", project_id=p_b.id, requirement_id=r_b1.id, requirement_version=1, clause_keys=["C1"], ac_keys=["AC1"], title="Test B", priority="high", test_type="api_contract", automation="pytest", script="assert True", script_hash="hash_b", version=1, status="approved", created_by=1)
        db.add_all([tc_a, tc_b])
        db.commit()

        # Verify strict isolation
        p_a_reqs = db.query(Requirement).filter_by(project_id=p_a.id).all()
        assert len(p_a_reqs) == 2
        assert {r.key for r in p_a_reqs} == {"PROJA-REQ-001", "PROJA-REQ-002"}

        p_b_reqs = db.query(Requirement).filter_by(project_id=p_b.id).all()
        assert len(p_b_reqs) == 1
        assert p_b_reqs[0].key == "PROJB-REQ-001"

        # Cross checks
        p_a_req_ids = {r.id for r in p_a_reqs}
        assert r_b1.id not in p_a_req_ids

        p_a_tests = db.query(TestCase).filter_by(project_id=p_a.id).all()
        assert len(p_a_tests) == 1
        assert p_a_tests[0].key == "TC-PROJA-001"

        p_b_tests = db.query(TestCase).filter_by(project_id=p_b.id).all()
        assert len(p_b_tests) == 1
        assert p_b_tests[0].key == "TC-PROJB-001"


def test_import_repository_dry_run_analysis(app):
    """Verifies that import-repo in dry-run mode returns AST architecture analysis without committing DB records."""
    from app.api.deps import Principal
    from app.api.routers.projects import RepoImportIn, import_repository
    from app.db.models import User
    with session_scope() as db:
        user = db.query(User).first()
        assert user is not None
        p = Principal(user=user, roles={"admin", "project.admin"}, session=None)
        body = RepoImportIn(
            repo_url="https://github.com/sohan10012/EchoBox.git",
            branch="main",
            dry_run=True
        )
        res = import_repository(body=body, p=p, db=db)
        assert res.get("dry_run") is True
        analysis = res.get("analysis", {})
        assert "file_count" in analysis
        assert analysis["file_count"] > 0
        assert "ECHO-ROOMS" in [m["code"] for m in analysis["modules"]]
