"""URL and Git ref validation for repository ingestion."""
from __future__ import annotations

import re

from app.core.errors import BadRequest


def validate_github_url(url: str) -> tuple[str, str]:
    """Strictly validates GitHub repository URLs, preventing SSRF, file schemes, and local IPs."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise BadRequest("Repository URL is required")
    # Enforce https:// scheme and github.com host
    m = re.match(r"^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$", cleaned)
    if not m:
        raise BadRequest("Invalid repository URL. Only public and private https://github.com/owner/repo URLs are supported.")
    owner, repo = m.group(1), m.group(2)
    # Reject path traversal or illegal names
    if ".." in owner or ".." in repo or owner.startswith(".") or repo.startswith("."):
        raise BadRequest("Invalid repository owner or name format.")
    return owner, repo


def validate_git_ref(ref: str) -> str:
    """Validates branch or commit ref, preventing git command option injection."""
    cleaned = (ref or "").strip()
    if not cleaned:
        return "main"
    if cleaned.startswith("-") or not re.match(r"^[a-zA-Z0-9_./-]+$", cleaned):
        raise BadRequest(f"Invalid branch or commit reference: {ref}")
    if ".." in cleaned or "/." in cleaned:
        raise BadRequest("Branch or commit reference cannot contain relative traversal sequences.")
    return cleaned
