"""Command line interface: ``security-txt-check example.com --file public/.well-known/security.txt``."""

from __future__ import annotations

import argparse
import functools
import os
import sys
from collections.abc import Sequence

from . import __version__
from .engine import EXIT_USAGE, Target, UsageError, parse_fail_on, parse_list, parse_target, run
from .fetch import fetch
from .report import to_json, to_text
from .rules import Options


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="security-txt-check",
        description=(
            "Validate security.txt (RFC 9116) for domains, https URLs or local files: "
            "required fields, Expires and the OpenPGP signature."
        ),
    )
    p.add_argument(
        "targets",
        nargs="*",
        help="domain(s) or https URL(s); a domain checks https://<domain>/.well-known/security.txt",
    )
    p.add_argument("--file", "-f", action="append", default=[], metavar="PATH", help="local security.txt to check")
    p.add_argument(
        "--fail-on",
        default="error",
        help="error (default), warn, info, none, and/or a comma list of finding ids",
    )
    p.add_argument(
        "--expires-warn-days",
        type=int,
        default=30,
        metavar="DAYS",
        help="warn when Expires is less than DAYS away (default 30)",
    )
    p.add_argument(
        "--signing-key",
        metavar="PATH",
        help="OpenPGP public key file; verify signatures with gpg against it",
    )
    p.add_argument("--timeout", type=float, default=10.0, help="HTTPS timeout per request in seconds")
    p.add_argument("--json", action="store_true", help="print JSON instead of text")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def build_targets(values: Sequence[str], files: Sequence[str]) -> list[Target]:
    targets = [parse_target(v) for v in parse_list(values)]
    for path in files:
        if not os.path.isfile(path):
            raise UsageError(f"file not found: {path}")
        targets.append(Target(path, path=path))
    if not targets:
        raise UsageError("give at least one domain, URL or --file")
    return targets


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        targets = build_targets(args.targets, args.file)
        fail_on = parse_fail_on(args.fail_on)
        if args.expires_warn_days < 0:
            raise UsageError("--expires-warn-days must be 0 or more")
        if args.signing_key and not os.path.isfile(args.signing_key):
            raise UsageError(f"signing key not found: {args.signing_key}")
    except UsageError as exc:
        print(f"security-txt-check: {exc}", file=sys.stderr)
        return EXIT_USAGE
    opts = Options(expires_warn_days=args.expires_warn_days, signing_key=args.signing_key)
    report = run(targets, opts, fail_on, functools.partial(fetch, timeout=args.timeout))
    print(to_json(report) if args.json else to_text(report))
    return report.exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
