"""GitHub REST integration. Success is only reported after GitHub confirms it."""
from __future__ import annotations

import base64

import httpx

from app.core.config import get_settings


class GitHubError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def configured() -> bool:
    return bool(get_settings().github_token)


def _client() -> httpx.Client:
    s = get_settings()
    if not s.github_token:
        raise GitHubError("GitHub is not configured (set GITHUB_TOKEN)")
    return httpx.Client(base_url=s.github_api_url, timeout=20, headers={
        "Authorization": f"Bearer {s.github_token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "TraceTest-AI"})


def _check(r: httpx.Response) -> dict:
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", r.text)
        except Exception:
            msg = r.text
        raise GitHubError(f"GitHub API error {r.status_code}: {str(msg)[:300]}", r.status_code)
    return r.json() if r.content else {}


def get_repo(repo: str) -> dict:
    with _client() as c:
        return _check(c.get(f"/repos/{repo}"))


def list_branches(repo: str) -> list[str]:
    with _client() as c:
        return [b["name"] for b in _check(c.get(f"/repos/{repo}/branches", params={"per_page": 100}))]


def get_commit(repo: str, ref: str) -> dict:
    with _client() as c:
        d = _check(c.get(f"/repos/{repo}/commits/{ref}"))
        return {"sha": d["sha"], "message": d["commit"]["message"], "url": d["html_url"]}


def create_issue(repo: str, title: str, body: str, labels: list[str]) -> dict:
    with _client() as c:
        d = _check(c.post(f"/repos/{repo}/issues", json={"title": title, "body": body, "labels": labels}))
    if not d.get("number") or not d.get("html_url"):
        raise GitHubError("GitHub did not confirm issue creation")
    return {"number": d["number"], "url": d["html_url"], "state": d.get("state", "open")}


def get_issue(repo: str, number: int) -> dict:
    with _client() as c:
        d = _check(c.get(f"/repos/{repo}/issues/{number}"))
    return {"number": d["number"], "state": d["state"], "url": d["html_url"]}


def put_file(repo: str, branch: str, path: str, content: str, message: str) -> dict:
    with _client() as c:
        sha = None
        r = c.get(f"/repos/{repo}/contents/{path}", params={"ref": branch})
        if r.status_code == 200:
            sha = r.json().get("sha")
        body = {"message": message, "content": base64.b64encode(content.encode()).decode(), "branch": branch}
        if sha:
            body["sha"] = sha
        d = _check(c.put(f"/repos/{repo}/contents/{path}", json=body))
    return {"path": path, "commit": d.get("commit", {}).get("sha")}
