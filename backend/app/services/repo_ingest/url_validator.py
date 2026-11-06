"""URL and Git ref validation for repository ingestion with DNS rebinding defenses."""
from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable

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


def resolve_and_validate_github_url(
    url: str,
    resolver: Callable[[str], list[str]] | None = None,
) -> tuple[str, str, str]:
    """Validates URL and resolves hostname, asserting the target IP is public (defeating DNS rebinding).

    Returns:
        tuple[owner, repo, pinned_ip]
    """
    owner, repo = validate_github_url(url)
    host = "github.com"

    resolved_ips: list[str] = []
    if resolver is not None:
        resolved_ips = resolver(host)
    else:
        try:
            addr_info = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                if ip_str not in resolved_ips:
                    resolved_ips.append(ip_str)
        except Exception as exc:
            raise BadRequest(f"DNS resolution failed for '{host}': {exc}") from exc

    if not resolved_ips:
        raise BadRequest(f"No IP addresses resolved for '{host}'")

    # Validate each resolved address
    for ip_str in resolved_ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError as exc:
            raise BadRequest(f"Invalid IP address format: {ip_str}") from exc

        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            raise BadRequest(
                f"Resolved IP address '{ip_str}' is private or disallowed. DNS rebinding rejected."
            )

    # Prefer IPv4 public address for curloptResolve compatibility
    ipv4_list = [ip for ip in resolved_ips if ":" not in ip]
    pinned_ip = ipv4_list[0] if ipv4_list else resolved_ips[0]

    return owner, repo, pinned_ip


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
