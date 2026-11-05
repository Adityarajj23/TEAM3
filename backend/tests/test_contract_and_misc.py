import json
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
REQUIRED = [("post", "/api/v1/requirements"), ("get", "/api/v1/requirements"),
            ("post", "/api/v1/requirements/{req_id}/analyse"), ("post", "/api/v1/requirements/{req_id}/generate-tests"),
            ("get", "/api/v1/requirements/{req_id}/versions"), ("get", "/api/v1/requirements/{req_id}/impact-analysis"),
            ("post", "/api/v1/tests/{test_id}/review"), ("post", "/api/v1/suites/{suite_id}/execute"),
            ("get", "/api/v1/executions/{ex_id}"), ("get", "/api/v1/executions/{ex_id}/logs"),
            ("post", "/api/v1/executions/{ex_id}/retry"), ("post", "/api/v1/executions/{ex_id}/analyse-failure"),
            ("post", "/api/v1/defects"), ("post", "/api/v1/defects/{defect_id}/approve"),
            ("post", "/api/v1/defects/{defect_id}/github-issue"), ("get", "/api/v1/traceability/matrix"),
            ("get", "/api/v1/analytics/dashboard"), ("post", "/api/v1/evaluations/run"), ("get", "/api/v1/audit"),
            ("get", "/api/v1/health"), ("get", "/api/v1/config")]


def test_required_endpoints_exist(app):
    spec = app.openapi()
    for method, path in REQUIRED:
        assert method in spec["paths"].get(path, {}), f"missing {method.upper()} {path}"


def test_openapi_has_not_drifted(app):
    """Run `make openapi` after intentional API changes."""
    assert DOCS.exists(), "docs/openapi.json missing — run make openapi"
    committed = json.loads(DOCS.read_text())
    assert committed["paths"].keys() == app.openapi()["paths"].keys()
    assert committed == json.loads(json.dumps(app.openapi()))


def test_error_envelope(qa):
    r = qa.get("/requirements/999999")
    e = r.json()["error"]
    assert r.status_code == 404 and set(e) == {"code", "message", "details", "trace_id"}
    r = qa.post("/requirements", json={"project_id": 1})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_github_not_configured_offers_download(qa, reviewer):
    d = qa.get("/defects?page_size=1").json()["items"][0]
    r = qa.post(f"/defects/{d['id']}/github-issue")
    assert r.status_code == 409 and r.json()["error"]["code"] == "github_not_configured"
    assert qa.get(f"/defects/{d['id']}/report.md").status_code == 200
    assert qa.get(f"/defects/{d['id']}/report.json").status_code == 200


def test_github_api_failure_is_reported(qa, admin, monkeypatch):
    from app.integrations import github
    monkeypatch.setattr(github, "configured", lambda: True)

    def boom(*a, **k):
        raise github.GitHubError("GitHub API error 500: boom", 500)
    monkeypatch.setattr(github, "get_repo", boom)
    monkeypatch.setattr(github, "create_issue", boom)
    pay = next(p for p in admin.get("/projects").json()["items"] if p["key"] == "PAY")
    out = admin.put(f"/integrations/github/{pay['id']}", json={"repo": "northwind/hcm", "branch": "main"}).json()
    assert out["status"] == "error"
    d = qa.get(f"/defects?project_id={pay['id']}&page_size=1&open_only=true").json()["items"][0]
    r = qa.post(f"/defects/{d['id']}/github-issue")
    assert r.status_code == 502 and qa.get(f"/defects/{d['id']}").json()["github_issue_url"] is None


def test_upload_txt_and_rejects_bad_pdf(qa):
    pay = next(p for p in qa.get("/projects").json()["items"] if p["key"] == "PAY")
    r = qa.post("/requirements/upload", data={"project_id": pay["id"], "title": "Uploaded overtime note"},
                files={"file": ("req.md", b"# Overtime\n- Hours above 40 must be overtime.\n- Rate is 1.5 times.", "text/markdown")})
    assert r.status_code == 201, r.text
    assert len(r.json()["clauses"]) == 2 and r.json()["source_type"] == "md"
    r = qa.post("/requirements/upload", data={"project_id": pay["id"], "title": "Bad pdf upload"},
                files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400


def test_defect_state_machine(qa):
    d = qa.get("/defects?status=open&page_size=1").json()["items"][0]
    assert qa.post(f"/defects/{d['id']}/transition", json={"status": "closed"}).status_code in (200, 409)
    d2 = qa.get("/defects?status=triaged&page_size=1").json()["items"]
    if d2:
        assert qa.post(f"/defects/{d2[0]['id']}/transition", json={"status": "verified"}).status_code == 409


def test_mock_evaluation_is_labelled_fixture(qa):
    r = qa.post("/evaluations/run", json={"provider": "mock"})
    assert r.status_code == 202
    ev = qa.get(f"/evaluations/{r.json()['eval_run_id']}").json()
    assert ev["is_fixture"] is True and ev["status"] in ("completed", "degraded")
    assert len(ev["results"]) == 10 and "schema_pass_rate" in ev["metrics"]
    assert qa.post("/evaluations/run", json={"provider": "groq"}).status_code == 409


def test_sse_stream(qa):
    r = qa.post("/evaluations/run", json={"provider": "mock"}).json()
    with qa.c.stream("GET", f"/api/v1/runs/{r['run_id']}/events") as s:
        body = "".join(chunk for chunk in s.iter_text())
    assert "data:" in body and "event: done" in body


def test_ci_results_ingestion(app, qa, monkeypatch):
    from fastapi.testclient import TestClient
    junit = ('<testsuites><testsuite name="pytest"><testcase classname="test_tc_pay_0001" name="test_x" time="0.01">'
             '<failure message="assert 1 == 0">trace</failure></testcase>'
             '<testcase classname="test_tc_pay_0002" name="test_y" time="0.01"/></testsuite></testsuites>')
    c = TestClient(app)
    body = {"project_key": "PAY", "environment": "1.0", "commit_sha": "abc1234", "branch": "main", "junit_xml": junit}
    assert c.post("/api/v1/ci/results", json=body).status_code == 401
    monkeypatch.setenv("TRACETEST_CI_TOKEN", "ci-secret")
    r = c.post("/api/v1/ci/results", json=body, headers={"Authorization": "Bearer ci-secret"})
    assert r.status_code == 201 and r.json()["status"] == "failed"
    ex = qa.get("/executions?source=ci&page_size=1").json()["items"][0]
    assert ex["commit_sha"] == "abc1234" and ex["passed"] == 1 and ex["failed"] == 1
