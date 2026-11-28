# Changelog

Releases are published to PyPI from GitHub Actions when a `v<version>` tag is pushed (see `.github/workflows/release.yml`). Each release needs an entry here with the same version.

## Unreleased

## 0.1.0 (unreleased)

First version.

- GitHub Action and CLI that validate security.txt (RFC 9116) on live sites (`/.well-known/security.txt`, with a warning for the legacy `/security.txt`) and in repository files.
- `Expires` checks: missing, repeated, invalid, expired, expiring within `expires-warn-days` (default 30) and more than a year away.
- OpenPGP cleartext signature checks: structure, CRC24, signature packet, weak hashes, unsigned content, and verification with `gpg` against a given key.
- `fail-on` by severity and/or finding id, job summary, annotations, JSON output and an optional tracking issue.
