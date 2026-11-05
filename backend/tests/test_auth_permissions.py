def test_login_rejects_bad_password_and_throttles(anon):
    for _ in range(5):
        r = anon.post("/auth/login", json={"email": "nobody@northwind-hcm.example", "password": "wrong"})
        assert r.status_code == 401
    r = anon.post("/auth/login", json={"email": "nobody@northwind-hcm.example", "password": "wrong"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "login_throttled"


def test_session_cookie_flags(app):
    from fastapi.testclient import TestClient
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"email": "qa.engineer@northwind-hcm.example", "password": "test-qa-password-12"})
    cookie = r.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert "password" not in r.text.lower()


def test_unauthenticated_requests_rejected(anon):
    r = anon.get("/projects")
    assert r.status_code == 401
    body = r.json()["error"]
    assert body["code"] == "unauthenticated" and body["trace_id"]


def test_csrf_required_for_mutations(qa):
    r = qa.c.post("/api/v1/requirements/1/analyse")
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"


def test_roles_and_permissions(admin, qa, reviewer):
    assert "admin" in admin.me["roles"] and "qa_engineer" in qa.me["roles"] and "reviewer" in reviewer.me["roles"]
    # reviewer cannot author requirements
    r = reviewer.post("/requirements", json={"project_id": 1, "title": "Reviewer attempt", "description": "Should not be allowed."})
    assert r.status_code == 403
    # qa cannot create projects or users
    assert qa.post("/projects", json={"key": "ZZZ", "name": "Blocked project"}).status_code == 403
    assert qa.post("/users", json={"email": "x@northwind-hcm.example", "full_name": "X", "roles": ["qa_engineer"]}).status_code == 403
    # qa cannot approve defects; reviewer cannot execute suites
    assert qa.post("/defects/1/approve", json={}).status_code == 403
    assert reviewer.post("/suites/1/execute", json={"environment_id": 1}).status_code == 403
    # admin can create projects
    r = admin.post("/projects", json={"key": "CRM", "name": "Customer Relationship Management"})
    assert r.status_code == 201, r.text


def test_project_isolation(admin, reviewer):
    ben = next(p for p in admin.get("/projects").json()["items"] if p["key"] == "BEN")
    assert reviewer.get(f"/projects/{ben['id']}").status_code == 404
    assert ben["id"] not in [p["id"] for p in reviewer.get("/projects").json()["items"]]
    reqs = reviewer.get(f"/requirements?project_id={ben['id']}")
    assert reqs.status_code == 404
    ben_req = admin.get(f"/requirements?project_id={ben['id']}&page_size=1").json()["items"][0]
    assert reviewer.get(f"/requirements/{ben_req['id']}").status_code == 404


def test_authors_cannot_approve_own_tests(qa, admin):
    req = qa.get("/requirements?status=analysed&page_size=1").json()["items"][0]
    detail = qa.get(f"/requirements/{req['id']}").json()
    clause = detail["clauses"][0]
    t = qa.post("/tests", json={"requirement_id": req["id"], "title": "Manual check of first clause",
                                "clause_keys": [clause["clause_key"]], "steps": [{"action": "Do the thing"}],
                                "expected_result": "Works", "source_quote": clause["text"]}).json()
    assert t["validation_status"] == "valid", t["validation_errors"]
    r = qa.post(f"/tests/{t['id']}/review", json={"decision": "approve"})
    assert r.status_code == 403  # QA lacks test.review permission entirely


def test_rate_limiting(app, monkeypatch):
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 3)
    c = TestClient(app)
    codes = [c.get("/api/v1/health", headers={}).status_code for _ in range(5)]
    assert 429 in codes
