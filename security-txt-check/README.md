# security-txt-check

> **Draft.** This folder is the first version of a standalone `lookproof/security-txt-check` repository. It has not been released: there is no `@v1` tag and no PyPI package yet. Until then, run it from this folder (see [Try it from this repository](#try-it-from-this-repository)).

Validates [security.txt](https://www.rfc-editor.org/rfc/rfc9116) (RFC 9116) in CI. It warns before `Expires` runs out and checks the OpenPGP signature. It is a GitHub Action and a command line tool, and both use the same engine. Made by [Lookproof](https://lookproof.dev), which checks DNS, TLS, HTTP headers and email security for domains.

It checks live sites (`https://<domain>/.well-known/security.txt`) and files in your repository before you deploy them. All checks run locally: the tool sends no data to Lookproof or anyone else and has no telemetry. It needs no Python packages outside the standard library. Signature verification uses `gpg`, if you pass a key.

## What it checks

| Area | Checks |
| --- | --- |
| Location | Fetched over HTTPS with certificate and host name validation. Falls back to `/security.txt` (warning) when `/.well-known/security.txt` is missing. An HTML page returned with status 200 (a catch-all route) counts as missing. Follows up to 5 redirects, only to `https://`, and warns when a redirect leaves the site. |
| Response | Status 200, `Content-Type: text/plain`, `charset=utf-8` (warning if missing), at most 64 KiB, valid UTF-8. |
| Syntax | Every line is a comment, blank or `Field: value` (RFC 9116 section 4). Unknown fields are reported as info, with a hint for common misspellings such as `Acknowledgements`. |
| Fields | At least one `Contact`. `Contact`, `Encryption`, `Acknowledgments`, `Canonical`, `Policy`, `Hiring` and `CSAF` hold URIs with an allowed scheme, and `http://` is an error. `Preferred-Languages` appears at most once and holds language tags. If `Canonical` is set, the URL the file was fetched from must be one of its values. |
| Expires | Exactly one `Expires`, an RFC 3339 date-time. An error once it has passed, a warning less than 30 days before (configurable) and a warning when it is more than a year away (RFC 9116 recommends less than a year). |
| Signature | Unsigned files get an info finding, and you can make it fail with `fail-on`. For signed files it checks the cleartext signature structure (armor, dash escaping, base64, CRC24 checksum, signature packet) and warns about MD5, SHA-1 and RIPEMD-160. It also flags text outside the signed part and a signed file without `Canonical`. With `signing-key`, it verifies the signature with `gpg` against that key only, in a throwaway keyring. |

A check that could not run (network error, TLS error, no `gpg` while a key was given) is reported as an error, so it never passes silently.

## Quick start

### Check the live file on pull requests and pushes

```yaml
# .github/workflows/security-txt.yml
name: security.txt
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  security-txt:
    runs-on: ubuntu-latest
    steps:
      - uses: lookproof/security-txt-check@v1
        with:
          domains: example.com, example.org
          fail-on: error
```

### Check the file in your repository before it is deployed

```yaml
jobs:
  security-txt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: lookproof/security-txt-check@v1
        with:
          files: public/.well-known/security.txt
          signing-key: .github/security-txt-signing-key.asc
          # Fail when the file expires within 60 days or is not signed.
          expires-warn-days: "60"
          fail-on: error,securitytxt-expires-soon,securitytxt-not-signed
```

### Daily check that opens an issue

The action opens one issue while the check fails, updates it on later runs, and closes it once the check passes. Issues are matched on their exact title. This is the simplest way to hear about an `Expires` date before it passes.

```yaml
# .github/workflows/security-txt-daily.yml
name: security.txt (daily)
on:
  schedule:
    - cron: "41 6 * * *"
  workflow_dispatch:

permissions:
  contents: read
  issues: write

jobs:
  security-txt:
    runs-on: ubuntu-latest
    steps:
      - uses: lookproof/security-txt-check@v1
        with:
          domains: example.com
          fail-on: warn
          create-issue: true
```

### Inputs

| Input | Default | Description |
| --- | --- | --- |
| `domains` | `""` | Comma-separated domains or `https://` URLs. A domain checks `https://<domain>/.well-known/security.txt`. |
| `files` | `""` | Comma-separated paths to security.txt files in the checked-out repository. Give `domains`, `files` or both. |
| `fail-on` | `error` | `error`, `warn`, `info` or `none`, and/or a comma list of finding ids. A severity fails on that severity or worse. Ids fail on that finding whatever its severity, e.g. `error,securitytxt-not-signed`. |
| `expires-warn-days` | `30` | Report `securitytxt-expires-soon` when `Expires` is less than this many days away. |
| `signing-key` | `""` | Path to an OpenPGP public key (armored or binary). Signatures are verified against this key only. Needs `gpg`, which `ubuntu-latest` has. |
| `create-issue` | `false` | Open, update and close one tracking issue. Needs `issues: write`. |
| `issue-title` | `security-txt-check: security.txt problems` | Title used to find the tracking issue. |
| `github-token` | `${{ github.token }}` | Token for `create-issue`. |
| `python-version` | `3.12` | Python used to run the tool. It is not added to `PATH` for later steps. |

### Outputs

| Output | Description |
| --- | --- |
| `json` | Every finding as JSON (same format as `security-txt-check --json`). |
| `exit-code` | `0` when nothing matches `fail-on`, `1` when something does, `2` on invalid input. |

The step exits with the same code, so a failing check fails the job. To keep going and read the result yourself, set `continue-on-error: true` on the step and read `steps.<id>.outputs.json`.

The action writes a table of findings to the job summary, with findings that match `fail-on` in bold, and adds those findings to the run as error annotations.

## Command line

```bash
pip install "git+https://github.com/lookproof/x402-examples.git#subdirectory=security-txt-check"
```

```bash
security-txt-check example.com --file public/.well-known/security.txt --signing-key key.asc
```

```
usage: security-txt-check [-h] [--file PATH] [--fail-on FAIL_ON]
                          [--expires-warn-days DAYS] [--signing-key PATH]
                          [--timeout TIMEOUT] [--json] [--version]
                          [targets ...]
```

`--file` can be repeated. The exit codes are the same as the action's: `0` passed, `1` a finding matched `--fail-on`, `2` invalid arguments.

Text output for a file with a bare email address in `Contact`, a misspelt field and 18 days left:

```
.well-known/security.txt
  error  securitytxt-invalid-uri *
         Line 1: Contact is not a URI (write mailto: in front of an email address)
         https://www.rfc-editor.org/rfc/rfc9116#section-2.5
  warn   securitytxt-expires-soon
         Expires 2026-12-10 00:00 UTC, in 18 days
         https://www.rfc-editor.org/rfc/rfc9116#section-2.5.5
  info   securitytxt-not-signed
         The file has no OpenPGP signature
         https://www.rfc-editor.org/rfc/rfc9116#section-2.3
  info   securitytxt-unknown-field
         Line 4: unknown field Acknowledgements; did you mean Acknowledgments?
         https://www.rfc-editor.org/rfc/rfc9116#section-2.4

FAILED (fail-on: error): 1 error, 1 warning, 2 info
* = matches fail-on
```

JSON output (`--json`), shortened:

```json
{
  "tool": "security-txt-check",
  "version": "0.1.0",
  "fail_on": "error",
  "failed": true,
  "exit_code": 1,
  "counts": { "error": 1, "warn": 1, "info": 2 },
  "targets": [
    {
      "target": ".well-known/security.txt",
      "source": ".well-known/security.txt",
      "findings": [
        {
          "id": "securitytxt-invalid-uri",
          "severity": "error",
          "check": "fields",
          "target": ".well-known/security.txt",
          "message": "Line 1: Contact is not a URI (write mailto: in front of an email address)",
          "url": "https://www.rfc-editor.org/rfc/rfc9116#section-2.5"
        }
      ]
    }
  ]
}
```

## Signing a security.txt

RFC 9116 recommends an OpenPGP cleartext signature, and a `Canonical` field so that the signed file cannot be served from someone else's site:

```bash
gpg --local-user security@example.com --clearsign --output security.txt security.txt.unsigned
```

```bash
gpg --armor --export security@example.com > .github/security-txt-signing-key.asc
```

Commit the exported public key and pass it as `signing-key`. The check then fails when the file changes without being signed again, or is signed by another key.

## Findings

Each finding links to the RFC 9116 section it is about, or to a page on [lookproof.dev/findings](https://lookproof.dev/findings) where one exists.

| Id | Severity | Meaning |
| --- | --- | --- |
| `securitytxt-not-found` | error | Neither `/.well-known/security.txt` nor `/security.txt` serves a file. |
| [`securitytxt-fetch-failed`](https://lookproof.dev/findings/https-unavailable) | error | Connection failed, or a status other than 200. |
| [`securitytxt-tls-error`](https://lookproof.dev/findings/tls-untrusted) | error | The certificate is not valid for the host, or the TLS handshake failed. |
| `securitytxt-insecure-redirect` | error | A redirect to `http://`. |
| [`securitytxt-too-many-redirects`](https://lookproof.dev/findings/redirect-limit) | error | More than 5 redirects. |
| `securitytxt-wrong-content-type` | error | Not `text/plain`. |
| `securitytxt-too-large` | error | Larger than 64 KiB. |
| `securitytxt-invalid-encoding` | error | Not valid UTF-8. |
| `securitytxt-syntax-error` | error | A line that is not a comment, a blank line or `Field: value`. |
| `securitytxt-contact-missing` | error | No `Contact` field. |
| `securitytxt-invalid-uri` | error | A URI field holds something that is not a URI, or uses a scheme the field does not allow. |
| `securitytxt-insecure-uri` | error | A URI field uses `http://`. |
| `securitytxt-field-repeated` | error | `Preferred-Languages` appears more than once. |
| `securitytxt-expires-missing` | error | No `Expires` field. |
| `securitytxt-expires-multiple` | error | More than one `Expires` field. |
| `securitytxt-expires-invalid` | error | `Expires` is not an RFC 3339 date-time. |
| `securitytxt-expired` | error | `Expires` has passed. |
| `securitytxt-signature-malformed` | error | The cleartext signature is broken: missing armor lines, a line not dash-escaped, bad base64 or checksum, no signature packet. |
| `securitytxt-unsigned-content` | error | Text before or after the signed part, which the signature does not cover. |
| `securitytxt-signature-invalid` | error | `gpg` reports a bad signature, a revoked key, or a signature by another key than `signing-key`. |
| `securitytxt-signature-check-failed` | error | A key was given but the signature could not be checked (no `gpg`, key not importable). |
| `securitytxt-legacy-location` | warn | Found only at `/security.txt`, not at `/.well-known/security.txt`. |
| [`securitytxt-redirect-offsite`](https://lookproof.dev/findings/redirect-offsite) | warn | A redirect to another site. |
| `securitytxt-no-charset` | warn | `Content-Type` has no `charset=utf-8`. |
| `securitytxt-expires-soon` | warn | `Expires` is less than `expires-warn-days` away. |
| `securitytxt-expires-too-far` | warn | `Expires` is more than a year away. |
| `securitytxt-invalid-language` | warn | `Preferred-Languages` holds something that is not a language tag. |
| `securitytxt-canonical-mismatch` | warn | The file was fetched from a URL that is not listed in `Canonical`. |
| `securitytxt-signed-no-canonical` | warn | Signed, but without a `Canonical` field. |
| `securitytxt-signature-weak-hash` | warn | Signed with MD5, SHA-1 or RIPEMD-160. |
| `securitytxt-signature-key-expired` | warn | A good signature by a key that has expired. |
| `securitytxt-not-signed` | info | No OpenPGP signature. |
| `securitytxt-signature-not-verified` | info | Signed, but no `signing-key` was given, so only the structure was checked. |
| `securitytxt-unknown-field` | info | A field that is not in RFC 9116 or the IANA registry. |
| [`check-internal-error`](https://lookproof.dev/findings/check-internal-error) | error | A bug in security-txt-check. Please open an issue. |

## More checks with Lookproof

security-txt-check looks at one file. [Lookproof](https://lookproof.dev) checks the rest of a domain: [TLS certificates](https://lookproof.dev/tools/tls/certificate-check), [security headers](https://lookproof.dev/tools/http/security-headers), DNSSEC, and SPF, DKIM and DMARC for email. Use the [site health check](https://lookproof.dev/tools/site/site-health-check) in the browser, through the [API](https://lookproof.dev/docs/api), or from AI agents through the [MCP server](../mcp-server/). For mail authentication in CI there is [dmarc-check](https://github.com/lookproof/dmarc-check).

## Try it from this repository

```bash
cd security-txt-check
pip install -e ".[dev]"
```

```bash
security-txt-check lookproof.dev
```

In a workflow in this repository, use the action from the checkout: `uses: ./security-txt-check`.

## Development

```bash
ruff check . && ruff format --check . && mypy && pytest
```

The unit tests use a fake HTTPS fetcher and need no network. The signature tests make throwaway keys with `gpg` and are skipped when it is not installed. `pytest -m network` checks that every lookproof.dev link exists in the lookproof.dev sitemap.

## License

MIT
