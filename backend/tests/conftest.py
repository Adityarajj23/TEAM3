"""Test configuration: isolated data dir, MockProvider (explicit test mode), inline background tasks."""
from __future__ import annotations

import os
import tempfile

_DATA = tempfile.mkdtemp(prefix="tracetest-test-")
os.environ.update({
    "TRACETEST_ENV": "test", "TRACETEST_DATA_DIR": _DATA, "TRACETEST_LLM_MODE": "mock",
    "TRACETEST_SEED_ON_STARTUP": "true",
    "TRACETEST_ADMIN_EMAIL": "admin@northwind-hcm.example",
    "TRACETEST_QA_EMAIL": "qa.engineer@northwind-hcm.example",
    "TRACETEST_REVIEWER_EMAIL": "reviewer@northwind-hcm.example",
    "TRACETEST_ADMIN_PASSWORD": "test-admin-password-1", "TRACETEST_QA_PASSWORD": "test-qa-password-12",
    "TRACETEST_REVIEWER_PASSWORD": "test-reviewer-password", "TRACETEST_RATE_LIMIT_PER_MINUTE": "100000",
    "TRACETEST_SECRET_KEY": "test-secret", "GROQ_API_KEY": "", "GROQ_API_KEY2": "", "GROQ_API_KEY3": "",
    "GROQ_KEY": "", "GROQ_KEY2": "", "GROQ_KEY3": "",
    "GEMINI_API_KEY": "", "GEMINI_API_KEY2": "", "GEMINI_API_KEY3": "",
    "GEMINI_KEY": "", "GEMINI_KEY2": "", "GEMINI_KEY3": "",
    "GITHUB_TOKEN": "",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.services import tasks  # noqa: E402

tasks.SYNC_MODE = True

ACCOUNTS = {
    "admin": ("admin@northwind-hcm.example", "test-admin-password-1"),
    "qa": ("qa.engineer@northwind-hcm.example", "test-qa-password-12"),
    "reviewer": ("reviewer@northwind-hcm.example", "test-reviewer-password"),
}


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app
    with TestClient(fastapi_app):  # runs lifespan -> migrations + seed
        yield fastapi_app


class Client:
    def __init__(self, app, role: str | None):
        self.c = TestClient(app)
        self.csrf = ""
        if role:
            email, pwd = ACCOUNTS[role]
            r = self.c.post("/api/v1/auth/login", json={"email": email, "password": pwd})
            assert r.status_code == 200, r.text
            self.csrf = r.json()["csrf_token"]
            self.me = r.json()

    def get(self, url, **kw):
        return self.c.get("/api/v1" + url, **kw)

    def _send(self, method, url, **kw):
        headers = kw.pop("headers", {}) or {}
        headers.setdefault("X-CSRF-Token", self.csrf)
        return self.c.request(method, "/api/v1" + url, headers=headers, **kw)

    def post(self, url, **kw):
        return self._send("POST", url, **kw)

    def patch(self, url, **kw):
        return self._send("PATCH", url, **kw)

    def put(self, url, **kw):
        return self._send("PUT", url, **kw)


@pytest.fixture(scope="session")
def admin(app):
    return Client(app, "admin")


@pytest.fixture(scope="session")
def qa(app):
    return Client(app, "qa")


@pytest.fixture(scope="session")
def reviewer(app):
    return Client(app, "reviewer")


@pytest.fixture
def anon(app):
    return Client(app, None)
