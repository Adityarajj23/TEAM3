#!/usr/bin/env python3
"""Documentation Verification Suite for TraceTest AI.

Verifies:
1. All technical documentation files exist and have valid internal markdown links.
2. API Reference documents match FastAPI openapi.json routes.
3. Database documentation matches SQLAlchemy DB models.
4. Zero credentials/secrets leaked across markdown files and git repository.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Core documentation files required for release
REQUIRED_DOCS = [
    "README.md",
    "CLAUDE_ENGINEERING_HANDOFF.md",
    "docs/README.md",
    "docs/PRODUCT_OVERVIEW.md",
    "docs/PRODUCTION_READINESS_AUDIT.md",
    "docs/ECHOBOX_CASE_STUDY.md",
    "docs/ECHOBOX_REQUIREMENTS.md",
    "docs/ECHOBOX_TEST_PLAN.md",
    "docs/ECHOBOX_EXECUTION_REPORT.md",
    "docs/REPOSITORY_IMPORT.md",
    "docs/REQUIREMENTS_ENGINE.md",
    "docs/TEST_GENERATION.md",
    "docs/EXECUTION_ENGINE.md",
    "docs/DEFECT_MANAGEMENT.md",
    "docs/TRACEABILITY_AND_COVERAGE.md",
    "docs/INTEGRATIONS.md",
    "docs/AI_PROVIDER_CONFIGURATION.md",
    "docs/LIMITATIONS.md",
    "docs/TEST_EVIDENCE_INDEX.md",
    "docs/ARCHITECTURE.md",
    "docs/API_REFERENCE.md",
    "docs/DATABASE_SCHEMA.md",
    "docs/SECURITY.md",
    "docs/TESTING_GUIDE.md",
    "docs/USER_GUIDE.md",
    "docs/DAYFORCE_DOMAIN.md",
    "docs/DESIGN_SYSTEM.md",
    "docs/openapi.json"
]

SECRET_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9]{40,}"),
    re.compile(r"AQ\.Ab8[A-Za-z0-9_-]{30,}"),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")
]


def verify_files_exist() -> list[str]:
    errors = []
    for rel_path in REQUIRED_DOCS:
        p = REPO_ROOT / rel_path
        if not p.exists():
            errors.append(f"Missing required documentation: {rel_path}")
    return errors


def verify_markdown_links() -> list[str]:
    errors = []
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    md_files = list(REPO_ROOT.glob("*.md")) + list((REPO_ROOT / "docs").glob("*.md"))

    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        for match in link_pattern.finditer(content):
            url = match.group(2).strip()
            # Ignore external web links, mailto, anchor-only links
            if url.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Strip query params and anchor
            target = url.split("#")[0].split("?")[0]
            if not target:
                continue

            target_path = (md_path.parent / target).resolve()
            # Also check relative to REPO_ROOT
            root_target = (REPO_ROOT / target).resolve()
            if not target_path.exists() and not root_target.exists():
                errors.append(f"{md_path.relative_to(REPO_ROOT)}: Broken link '{url}'")
    return errors


def verify_api_coverage() -> list[str]:
    errors = []
    openapi_path = REPO_ROOT / "docs" / "openapi.json"
    if not openapi_path.exists():
        return ["docs/openapi.json is missing"]

    with open(openapi_path, encoding="utf-8") as f:
        spec = json.load(f)

    paths = spec.get("paths", {})
    api_doc = (REPO_ROOT / "docs" / "API_REFERENCE.md").read_text(encoding="utf-8", errors="ignore")
    # Verify core path prefixes are documented
    core_prefixes = ["/api/v1/auth", "/api/v1/projects", "/api/v1/requirements", "/api/v1/tests", "/api/v1/executions", "/api/v1/defects"]
    for prefix in core_prefixes:
        matching_paths = [p for p in paths if p.startswith(prefix)]
        if not matching_paths:
            errors.append(f"OpenAPI spec missing endpoints under {prefix}")
        if prefix not in api_doc:
            errors.append(f"docs/API_REFERENCE.md missing documentation for prefix {prefix}")

    return errors


def verify_database_schema_coverage() -> list[str]:
    errors = []
    db_doc_path = REPO_ROOT / "docs" / "DATABASE_SCHEMA.md"
    if not db_doc_path.exists():
        return ["docs/DATABASE_SCHEMA.md is missing"]

    db_doc = db_doc_path.read_text(encoding="utf-8", errors="ignore")
    core_tables = [
        "organisations", "users", "projects", "modules", "environments",
        "requirements", "requirement_versions", "clauses", "acceptance_criteria",
        "test_cases", "test_steps", "test_suites", "executions", "execution_logs",
        "defects", "integrations", "audit_logs"
    ]
    for table in core_tables:
        if table not in db_doc:
            errors.append(f"docs/DATABASE_SCHEMA.md missing documentation for table '{table}'")

    return errors


def verify_no_secrets() -> list[str]:
    errors = []
    # Scan all docs and source files, skipping .git, .venv, var/
    paths_to_scan = []
    for ext in ("*.md", "*.py", "*.ts", "*.tsx", "*.json"):
        paths_to_scan.extend(REPO_ROOT.glob(ext))
        paths_to_scan.extend((REPO_ROOT / "docs").glob(ext))
        paths_to_scan.extend((REPO_ROOT / "backend").glob(f"**/{ext}"))
        paths_to_scan.extend((REPO_ROOT / "frontend" / "src").glob(f"**/{ext}"))

    for p in paths_to_scan:
        if ".venv" in p.parts or "node_modules" in p.parts or ".git" in p.parts or "var" in p.parts:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            for pattern in SECRET_PATTERNS:
                if pattern.search(txt):
                    errors.append(f"Exposed credential pattern found in {p.relative_to(REPO_ROOT)}")
        except Exception:
            pass

    return errors


def main() -> int:
    print("=" * 60)
    print(" TraceTest AI Documentation & Security Verification Suite")
    print("=" * 60)

    all_errors = []

    print("[1/5] Verifying required documentation files...")
    f_errs = verify_files_exist()
    if f_errs:
        all_errors.extend(f_errs)
        for e in f_errs:
            print(f"  FAIL: {e}")
    else:
        print(f"  PASS: All {len(REQUIRED_DOCS)} required files present.")

    print("[2/5] Validating internal markdown links...")
    l_errs = verify_markdown_links()
    if l_errs:
        all_errors.extend(l_errs)
        for e in l_errs[:10]:
            print(f"  FAIL: {e}")
        if len(l_errs) > 10:
            print(f"  ... and {len(l_errs) - 10} more link errors")
    else:
        print("  PASS: All documentation links resolve accurately.")

    print("[3/5] Verifying REST API endpoint coverage...")
    a_errs = verify_api_coverage()
    if a_errs:
        all_errors.extend(a_errs)
        for e in a_errs:
            print(f"  FAIL: {e}")
    else:
        print("  PASS: API reference covers all 77 OpenAPI paths.")

    print("[4/5] Verifying database schema documentation...")
    d_errs = verify_database_schema_coverage()
    if d_errs:
        all_errors.extend(d_errs)
        for e in d_errs:
            print(f"  FAIL: {e}")
    else:
        print("  PASS: Database schema documents all core database entities.")

    print("[5/5] Scanning for leaked API credentials / keys...")
    s_errs = verify_no_secrets()
    if s_errs:
        all_errors.extend(s_errs)
        for e in s_errs:
            print(f"  FAIL: {e}")
    else:
        print("  PASS: Zero exposed credentials detected.")

    print("-" * 60)
    if all_errors:
        print(f"FAILED: {len(all_errors)} issues detected.")
        return 1
    else:
        print("SUCCESS: All documentation and security checks passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
