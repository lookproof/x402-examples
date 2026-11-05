# Lookproof MCP server

<!-- mcp-name: io.github.lookproof/lookproof-mcp -->

An [MCP](https://modelcontextprotocol.io) server that gives Claude and other AI agents 23 [Lookproof](https://lookproof.dev) tools: domain and site health, SPF, DKIM, DMARC, MTA-STS, BIMI, DNS, DNSSEC, CAA, RDAP, TLS certificates and HTTP security headers. The agent pays per call in USDC on Base via x402, from a wallet you control, with a spending cap per session.

Every tool description states its price, so the agent can see what a call costs before making it. Without `X402_PAY=1` nothing is ever paid: every tool is a dry run that reports the price and returns no data.

```bash
uvx lookproof-mcp --version     # needs uv: https://docs.astral.sh/uv/
```

## Tools

| Tool | Price | Tool | Price |
|---|---|---|---|
| `get_spending` | free | `bimi` | $0.01 |
| `domain_health` | $0.08 | `mail_provider` | $0.005 |
| `site_health` | $0.025 | `spf_parse` | $0.002 |
| `mail_check` | $0.03 | `dmarc_parse` | $0.002 |
| `spf` | $0.01 | `dns_lookup` | $0.005 |
| `spf_flatten` | $0.01 | `dnssec` | $0.01 |
| `dmarc` | $0.01 | `caa` | $0.01 |
| `dkim` | $0.01 | `nameservers` | $0.01 |
| `dkim_discover` | $0.02 | `rdap` | $0.01 |
| `mta_sts` | $0.02 | `tls_certificate` | $0.01 |
| `tlsrpt` | $0.01 | `security_headers` | $0.01 |
| `mx` | $0.01 | | |
| `spoofable` | $0.01 | | |

`get_spending` is free and shows what the session has spent and how much budget is left.

## Endpoints without a tool

Lookproof has 47 paid endpoints. This server exposes the 23 an agent is most likely to need for questions about a domain's DNS and mail security, because every extra tool costs context and makes the agent's choice harder. The other 24, and why they are left out:

| Endpoints | Why left out |
|---|---|
| `POST /v1/mail/check/bulk` | Up to 20 domains in one paid call ($0.024 each, up to $0.48): too easy for an agent to spend the session budget at once. Use it from a script. |
| `GET /v1/dns/soa`, `/v1/dns/ttl`, `/v1/dns/wildcard`, `/v1/dns/https-rr`, `/v1/dns/compare`, `/v1/dns/ns-provider`, `/v1/dns/txt-verification`, `/v1/mail/ptr` | Specialised DNS diagnostics. `domain_health` (which includes reverse DNS of the mail servers) and `dns_lookup` answer the common questions. |
| `GET /v1/ip/info`, `/v1/ip/cidr`, `/v1/ip/subnets`, `/v1/ip/range-to-cidr`, `POST /v1/ip/contains`, `GET /v1/dns/idn` | Offline IP arithmetic and IDN conversion. An agent can do this itself without paying. |
| `POST /v1/dns/zone-lint`, `/v1/tls/pem-decode`, `/v1/tls/csr-decode`, `/v1/http/csp-parse`, `/v1/http/hsts-parse`, `/v1/http/cookie-parse`, `/v1/mail/mta-sts-parse`, `/v1/mail/bimi-parse`, `/v1/mail/tlsrpt-parse` | Parsers for text the user pastes. They fit a script better than an agent session, and pasted cookies or zone files can contain data the user may not want to send. `spf_parse` and `dmarc_parse` are included as examples of this kind of tool. |

All of them are in [`docs/endpoints.md`](https://github.com/lookproof/x402-examples/blob/master/docs/endpoints.md). To add one, copy a tool in `src/lookproof_mcp/server.py`, set its path and price, and run `uv run lookproof-mcp --check`.

## Setup

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.

Store the wallet key in a file only you can read, so it never sits in an MCP client's config file:

```bash
install -m 600 /dev/null ~/.lookproof-wallet.key
nano ~/.lookproof-wallet.key        # paste the private key, save
```

The server runs with [uv](https://docs.astral.sh/uv/)'s `uvx`, which downloads `lookproof-mcp` from PyPI into its own environment, with exactly the dependency versions this release was tested with. There is nothing to clone or install by hand. Try it without a wallet first: with no settings, every tool is a dry run.

## Settings

| Variable | Default | Effect |
|---|---|---|
| `X402_PAY` | off | Without `X402_PAY=1`, every tool runs as a dry run: it reports the price and returns no data. |
| `PRIVATE_KEY_FILE` | | Path to a file with the wallet's private key (recommended). It must not be readable by other users. |
| `PRIVATE_KEY` | | The key itself, if you prefer an environment variable. |
| `PAYTO_ALLOWLIST` | empty | Optional comma-separated addresses; a 402 asking for payment to any other address is refused before signing. See [pinning the receiving address](https://github.com/lookproof/x402-examples#pinning-the-receiving-address-payto_allowlist). |
| `MAX_SPEND_USD` | `0.10` | Spending cap for the session (one server process). Calls beyond it are refused, not paid. |

How payments are limited is described under [Security](#security).

## Claude Code

```bash
claude mcp add lookproof \
  --env X402_PAY=1 \
  --env PRIVATE_KEY_FILE=$HOME/.lookproof-wallet.key \
  --env MAX_SPEND_USD=0.25 \
  -- uvx lookproof-mcp
```

Leave out `--env X402_PAY=1` to try it as a dry run first.

Then ask, for example: *"Is example.com protected against email spoofing? Check SPF, DMARC and MTA-STS."*

## Claude Desktop

Add this to `claude_desktop_config.json` (Settings, Developer, Edit Config) and restart Claude Desktop:

```json
{
  "mcpServers": {
    "lookproof": {
      "command": "uvx",
      "args": ["lookproof-mcp"],
      "env": {
        "X402_PAY": "1",
        "PRIVATE_KEY_FILE": "/home/you/.lookproof-wallet.key",
        "MAX_SPEND_USD": "0.25"
      }
    }
  }
}
```

If Claude Desktop can't find `uvx`, use its full path (`which uvx` on macOS and Linux, `where uvx` on Windows). On Windows, write the key path as `C:\\Users\\you\\.lookproof-wallet.key`.

## What a tool call returns

Paid (shape only, not yet verified against the live API; `data` is the full Lookproof response):

```json
{
  "data": {"endpoint": "mail.dmarc", "status": "<ok|info|warning|error|unknown>", "data": {"policy": "...", "...": "..."}, "findings": ["..."]},
  "cost_usd": 0.01,
  "session_spent_usd": 0.01,
  "session_remaining_usd": 0.09,
  "tx": "https://basescan.org/tx/0x<transaction-hash>"
}
```

Dry run (no `X402_PAY=1`):

```json
{"dry_run": true, "would_cost_usd": 0.08, "network": "eip155:8453", "pay_to": "0x<lookproof-address>",
 "note": "Dry run, nothing paid and no data. The user can set X402_PAY=1 to enable payments."}
```

When the cap is reached:

```json
{"error": "Session spending cap reached: $0.090 spent of MAX_SPEND_USD=$0.1; this call costs $0.080. Restart the server or raise MAX_SPEND_USD."}
```

## Security

- **Dedicated wallet.** Use a wallet that only holds what you are willing to spend on checks, never your main wallet. Prefer `PRIVATE_KEY_FILE` over `PRIVATE_KEY`, so the key is not in the MCP client's config file; the server refuses a key file that other users can read.
- **Dry run by default.** Nothing is signed or paid unless `X402_PAY=1` is set.
- **Spending cap.** `MAX_SPEND_USD` (default $0.10) caps what one server process can spend. The cost of a call is reserved before paying, so parallel calls cannot overshoot it, and a call that fails after the payment was signed stays counted and is reported as "possibly paid".
- **Price check.** A tool refuses to pay more than the price in its description.
- **Locked payment.** Each payment is locked to the amount, asset (USDC), network (Base, `eip155:8453`) and `payTo` address of the 402 the server just received for that call. If the second 402 asks for anything else, nothing is signed. With `PAYTO_ALLOWLIST`, a `payTo` outside the list is refused before signing.
- **Results are data.** Tool results contain records and web content published by the checked domain's owner. The agent is told to treat them as data, and the cap and price checks apply whatever it is told.
- **Identifiable client.** Every request carries `User-Agent: lookproof-mcp/<version>`.

## Command line

| Command | Effect |
|---|---|
| `uvx lookproof-mcp` | Runs the MCP server on stdio (what Claude Code and Claude Desktop start). |
| `uvx lookproof-mcp --check` | Compares every tool's advertised price with the live 402 response. Pays nothing and needs no wallet. |
| `uvx lookproof-mcp --version` | Prints the version. |

## Run from source

```bash
git clone https://github.com/lookproof/x402-examples.git
cd x402-examples/mcp-server
uv run lookproof-mcp            # or: uv run lookproof-mcp --check
```

Source, issues and the other x402 examples (quickstart, domain monitor): [github.com/lookproof/x402-examples](https://github.com/lookproof/x402-examples).
