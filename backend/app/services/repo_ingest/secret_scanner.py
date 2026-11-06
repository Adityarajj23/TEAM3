"""Repository secret scanner: detects API keys, tokens, and credentials."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def scan_for_secrets(repo_path: Path) -> list[dict[str, Any]]:
    """Scans repository files for credentials, private keys, and environment variables."""
    findings: list[dict[str, Any]] = []
    secret_patterns = [
        ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
        ("GitHub Personal Access Token", re.compile(r"\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b")),
        ("Generic Secret Assignment", re.compile(r"(?i)(?:api_key|secret_key|private_key)\s*[:=]\s*['\"][0-9a-zA-Z_\-]{24,}['\"]"))
    ]
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "dist", ".venv", "__pycache__")]
        for f in files:
            p = Path(root) / f
            rel = str(p.relative_to(repo_path))
            if f in (".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"):
                findings.append({"file": rel, "type": "Environment/Key File", "severity": "critical"})
                continue
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".ico", ".pdf", ".zip", ".tar", ".gz", ".pyc", ".db", ".sqlite"):
                continue
            if p.stat().st_size > 500000:
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for label, pat in secret_patterns:
                    if pat.search(content):
                        findings.append({"file": rel, "type": label, "severity": "high"})
            except Exception:
                pass
    return findings

