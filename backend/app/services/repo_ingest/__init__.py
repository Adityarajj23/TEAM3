"""Repository Ingestion Package: modularized components for URL validation, secret scanning, AST analysis, and requirement/test derivation."""
from __future__ import annotations

from app.services.repo_ingest.ast_analyzer import RepoAnalysisResult, analyze_repository
from app.services.repo_ingest.echobox_derivation import ingest_echobox_project
from app.services.repo_ingest.generic_derivation import ingest_generic_project
from app.services.repo_ingest.secret_scanner import scan_for_secrets
from app.services.repo_ingest.url_validator import validate_git_ref, validate_github_url

__all__ = [
    "validate_github_url",
    "validate_git_ref",
    "scan_for_secrets",
    "RepoAnalysisResult",
    "analyze_repository",
    "ingest_echobox_project",
    "ingest_generic_project",
]

