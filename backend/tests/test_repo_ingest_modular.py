"""Unit tests covering each modularized component of repo_ingest."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.core.errors import AppError
from app.services.repo_ingest.ast_analyzer import RepoAnalysisResult, analyze_repository
from app.services.repo_ingest.secret_scanner import scan_for_secrets
from app.services.repo_ingest.url_validator import validate_git_ref, validate_github_url


def test_url_validator_valid_and_invalid():
    owner, repo = validate_github_url("https://github.com/sohan10012/EchoBox.git")
    assert owner == "sohan10012"
    assert repo == "EchoBox"

    with pytest.raises(AppError):
        validate_github_url("ftp://github.com/a/b")

    with pytest.raises(AppError):
        validate_github_url("https://notgithub.com/a/b")


def test_git_ref_validator():
    assert validate_git_ref("feature/my-branch_1.0") == "feature/my-branch_1.0"
    assert validate_git_ref("") == "main"

    with pytest.raises(AppError):
        validate_git_ref("--upload-pack=exploit")

    with pytest.raises(AppError):
        validate_git_ref("branch/../escape")


def test_secret_scanner_detects_credentials():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Safe file
        (root / "safe.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
        # Leak file
        (root / "leak.py").write_text("AWS_KEY = 'AKIA1234567890ABCDEF'\n", encoding="utf-8")
        # Env file
        (root / ".env").write_text("DATABASE_URL=postgres://localhost\n", encoding="utf-8")

        findings = scan_for_secrets(root)
        types = {f["type"] for f in findings}
        assert "AWS Access Key" in types
        assert "Environment/Key File" in types


def test_ast_analyzer_discovers_structure():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health(): pass\n", encoding="utf-8")
        (root / "package.json").write_text('{"dependencies": {"react": "^18.0.0", "vite": "^5.0.0"}}', encoding="utf-8")

        res = analyze_repository(root)
        assert isinstance(res, RepoAnalysisResult)
        assert "Python" in res.languages
        assert "React" in res.frameworks
        assert "Vite" in res.frameworks
        assert any(ep["url"] == "/health" for ep in res.endpoints_found)

