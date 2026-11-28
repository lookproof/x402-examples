"""Maintain a single tracking issue through the GitHub REST API."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ISSUE_MARKER = "<!-- security-txt-check -->"


class GitHubError(Exception):
    pass


class GitHubClient:
    def __init__(self, token: str, repository: str, api_url: str = "https://api.github.com"):
        if not token:
            raise GitHubError("no GitHub token; pass github-token or grant the job a GITHUB_TOKEN")
        if "/" not in repository:
            raise GitHubError(f"invalid repository {repository!r}")
        self.token = token
        self.repository = repository
        if not api_url.startswith(("https://", "http://")):
            raise GitHubError(f"invalid GitHub API URL {api_url!r}")
        self.api_url = api_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(  # noqa: S310 - scheme checked in __init__
            f"{self.api_url}/repos/{self.repository}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "security-txt-check",
                **({"Content-Type": "application/json"} if data else {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            hint = " (does the job have 'issues: write' permission?)" if exc.code in (403, 404) else ""
            raise GitHubError(f"{method} {path}: HTTP {exc.code}{hint}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"{method} {path}: {exc.reason}") from exc
        return json.loads(raw) if raw else None

    def find_open_issue(self, title: str) -> dict[str, Any] | None:
        for page in range(1, 51):  # up to 5000 open issues
            query = urllib.parse.urlencode({"state": "open", "per_page": 100, "page": page})
            issues = self.request("GET", f"/issues?{query}")
            for issue in issues:
                if "pull_request" not in issue and issue.get("title") == title:
                    return dict(issue)
            if len(issues) < 100:
                break
        return None


def sync_issue(client: GitHubClient, title: str, failed: bool, body: str) -> str:
    """Create/update the issue when ``failed``; close it when not. Returns a log line."""
    issue = client.find_open_issue(title)
    body = f"{ISSUE_MARKER}\n{body}"
    if failed:
        if issue:
            client.request("PATCH", f"/issues/{issue['number']}", {"body": body})
            return f"Updated issue #{issue['number']}"
        created = client.request("POST", "/issues", {"title": title, "body": body})
        return f"Opened issue #{created['number']}"
    if issue:
        client.request(
            "POST",
            f"/issues/{issue['number']}/comments",
            {"body": "All security-txt-check checks pass now. Closing."},
        )
        client.request(
            "PATCH",
            f"/issues/{issue['number']}",
            {"state": "closed", "state_reason": "completed", "body": body},
        )
        return f"Closed issue #{issue['number']}"
    return "No open issue and nothing failing"
