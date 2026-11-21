"""Entry point for the GitHub Action (``python -m security_txt_check.action``).

Inputs arrive as ``SECURITY_TXT_CHECK_*`` environment variables set by action.yml.
"""

from __future__ import annotations

import os
import secrets
import sys
from collections.abc import Mapping

from .cli import build_targets
from .engine import EXIT_USAGE, UsageError, parse_fail_on, parse_list, run
from .fetch import Fetcher
from .github import GitHubClient, GitHubError, sync_issue
from .report import to_json, to_markdown, to_text
from .rules import Options
from .signature import Verifier

DEFAULT_ISSUE_TITLE = "security-txt-check: security.txt problems"
PREFIX = "SECURITY_TXT_CHECK_"


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def _append(path: str | None, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)


def _set_output(path: str | None, name: str, value: str) -> None:
    delimiter = f"EOF_{secrets.token_hex(8)}"
    _append(path, f"{name}<<{delimiter}\n{value}\n{delimiter}\n")


def main(
    env: Mapping[str, str] | None = None,
    fetcher: Fetcher | None = None,
    verifier: Verifier | None = None,
    client: GitHubClient | None = None,
) -> int:
    env = os.environ if env is None else env

    def get(name: str, default: str = "") -> str:
        return env.get(PREFIX + name, default)

    try:
        targets = build_targets(parse_list([get("DOMAINS")]), parse_list([get("FILES")]))
        fail_on = parse_fail_on(get("FAIL_ON", "error"))
        raw_days = get("EXPIRES_WARN_DAYS", "30").strip() or "30"
        if not raw_days.isdigit():
            raise UsageError(f"expires-warn-days must be a whole number of days, not {raw_days!r}")
        key = get("SIGNING_KEY").strip() or None
        if key and not os.path.isfile(key):
            raise UsageError(f"signing-key file not found: {key}")
    except UsageError as exc:
        print(f"::error title=security-txt-check::{_escape(str(exc))}")
        return EXIT_USAGE

    opts = Options(expires_warn_days=int(raw_days), signing_key=key, verifier=verifier)
    report = run(targets, opts, fail_on, fetcher)

    print(to_text(report))
    for f in report.failing:
        print(f"::error title=security-txt-check {f.id} ({_escape(f.target)})::{_escape(f.message)} {f.url}")

    _append(env.get("GITHUB_STEP_SUMMARY"), to_markdown(report))
    _set_output(env.get("GITHUB_OUTPUT"), "json", to_json(report))
    _set_output(env.get("GITHUB_OUTPUT"), "exit-code", str(report.exit_code))

    if _bool(get("CREATE_ISSUE", "false")):
        title = get("ISSUE_TITLE").strip() or DEFAULT_ISSUE_TITLE
        run_url = ""
        if env.get("GITHUB_RUN_ID"):
            server = env.get("GITHUB_SERVER_URL", "https://github.com")
            run_url = f"{server}/{env.get('GITHUB_REPOSITORY', '')}/actions/runs/{env['GITHUB_RUN_ID']}"
        body = to_markdown(report, heading="## security-txt-check report", footer=False)
        if run_url:
            body += f"\nLast checked by [this workflow run]({run_url}). "
        body += "This issue is updated by security-txt-check and closed automatically when the checks pass.\n"
        try:
            gh = client or GitHubClient(
                get("GITHUB_TOKEN"),
                env.get("GITHUB_REPOSITORY", ""),
                env.get("GITHUB_API_URL", "https://api.github.com"),
            )
            print(sync_issue(gh, title, report.failed, body))
        except GitHubError as exc:
            print(f"::error title=security-txt-check issue::{_escape(str(exc))}")
            return max(report.exit_code, 1)

    return report.exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
