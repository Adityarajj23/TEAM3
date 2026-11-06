"""Regression tests for P0-1: auto-admin access, CSRF bypass, bind host, Host/Origin validation."""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app as fastapi_app


def test_cross_origin_post_rejected(app):
    client = TestClient(app)
    # Attempt a cross-site POST from an untrusted origin
    resp = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://evil-attacker.example.com", "Host": "localhost"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    assert "cross_origin" in resp.text.lower() or "rejected" in resp.text.lower()


def test_bad_host_header_rejected(app):
    client = TestClient(app)
    resp = client.get(
        "/api/v1/health",
        headers={"Host": "malicious-site.example.com"},
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "host" in resp.text.lower()


def test_state_changing_post_without_csrf_rejected_even_in_single_operator(app, monkeypatch):
    # Verify that an unauthenticated state-changing POST cannot execute or bypass CSRF
    from app.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "app_env", "development")
    monkeypatch.setattr(s, "single_operator", True)

    client = TestClient(app)
    # An unauthenticated POST must NOT succeed with synthetic id=0 session
    resp = client.post("/api/v1/projects", json={"name": "Attacker Project", "key": "ATTACK"})
    assert resp.status_code == 401, f"Expected 401 unauthenticated, got {resp.status_code}: {resp.text}"


def test_single_operator_minting_and_csrf_enforcement(app, monkeypatch):
    from app.core.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "app_env", "development")
    monkeypatch.setattr(s, "single_operator", True)

    client = TestClient(app)
    # 1. GET /api/v1/auth/me sets real session cookie and returns csrf_token
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    csrf_token = me_resp.json().get("csrf_token")
    assert csrf_token and csrf_token != "operator-csrf"
    session_cookie = client.cookies.get("tt_session")
    assert session_cookie is not None

    # 2. State-changing POST without X-CSRF-Token is rejected with 403
    resp_no_csrf = client.post("/api/v1/projects", json={"name": "Legit Project", "key": "LEGIT"})
    assert resp_no_csrf.status_code == 403, f"Expected 403 for missing CSRF, got {resp_no_csrf.status_code}"
    assert "csrf" in resp_no_csrf.text.lower()

    # 3. State-changing POST with matching X-CSRF-Token succeeds
    resp_ok = client.post(
        "/api/v1/projects",
        json={"name": "Legit Project", "key": "LEGIT"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp_ok.status_code == 201





def test_single_operator_on_non_loopback_refuses_to_start():
    # If single_operator is True and bind_host is non-loopback (e.g. 0.0.0.0 or LAN IP), refuse to start
    with pytest.raises((RuntimeError, ValueError)) as exc:
        s = Settings(
            TRACETEST_ENV="development",
            TRACETEST_SINGLE_OPERATOR="true",
            TRACETEST_HOST="0.0.0.0",
        )
        s.validate_security_invariants()
    assert "loopback" in str(exc.value).lower() or "0.0.0.0" in str(exc.value).lower()


def test_production_mode_with_default_secret_refuses_to_start():
    with pytest.raises((RuntimeError, ValueError)) as exc:
        s = Settings(
            TRACETEST_ENV="production",
            TRACETEST_SECRET_KEY="change-me-in-env",
        )
        s.validate_security_invariants()
    assert "secret" in str(exc.value).lower()


def test_untrusted_repo_build_script_never_executed_on_host(tmp_path):
    import json
    from app.services.echobox_runner import run_tier_a_static

    marker_file = tmp_path / "p0_2_pwned_marker.txt"
    if marker_file.exists():
        marker_file.unlink()

    # Create dummy repo structure with malicious package.json build script
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir(parents=True)
    (backend_dir / "lambda_function.py").write_text("action = 'join'\n", encoding="utf-8")

    package_json = tmp_path / "package.json"
    package_json.write_text(
        json.dumps({
            "name": "malicious-repo",
            "scripts": {
                "build": f"touch {marker_file}"
            }
        }),
        encoding="utf-8"
    )

    # Run Tier A verification
    result = run_tier_a_static(tmp_path)

    # ASSERT: The build script MUST NEVER be executed on host, marker must not exist
    assert not marker_file.exists(), "CRITICAL P0-2 FAILURE: Untrusted repository build script was executed on the host!"
    assert result.get("typescript_build", {}).get("status") in ("passed", "skipped", "static_only")

