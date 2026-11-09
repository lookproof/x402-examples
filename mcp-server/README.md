# Lookproof MCP server

<!-- mcp-name: io.github.lookproof/lookproof-mcp -->

An [MCP](https://modelcontextprotocol.io) server that gives Claude and other AI agents 23 [Lookproof](https://lookproof.dev) tools: domain and site health, SPF, DKIM, DMARC, MTA-STS, BIMI, DNS, DNSSEC, CAA, RDAP, TLS certificates and HTTP security headers.

There are two ways to pay for the checks:

1. **API key (start here).** A [free key with 250 credits a month](https://lookproof.dev/pricing). Set `LOOKPROOF_API_KEY` and every call uses your plan's credits. No wallet, no crypto.
2. **x402.** The agent pays per call in USDC on Base, from a wallet you control, with a spending cap per session. No account needed.

With neither set, nothing is ever charged: every tool is a dry run that reports the price and returns no data.

```bash
uvx lookproof-mcp --version     # needs uv: https://docs.astral.sh/uv/
```

## Tools

| Tool | Credits | x402 price | Tool | Credits | x402 price |
|---|---|---|---|---|---|
| `get_spending` | free | free | `bimi` | 1 | $0.01 |
| `domain_health` | 5 | $0.08 | `mail_provider` | 1 | $0.005 |
| `site_health` | 5 | $0.025 | `spf_parse` | 1 | $0.002 |
| `mail_check` | 1 | $0.03 | `dmarc_parse` | 1 | $0.002 |
| `spf` | 1 | $0.01 | `dns_lookup` | 1 | $0.005 |
| `spf_flatten` | 1 | $0.01 | `dnssec` | 1 | $0.01 |
| `dmarc` | 1 | $0.01 | `caa` | 1 | $0.01 |
| `dkim` | 1 | $0.01 | `nameservers` | 1 | $0.01 |
| `dkim_discover` | 1 | $0.02 | `rdap` | 1 | $0.01 |
| `mta_sts` | 1 | $0.02 | `tls_certificate` | 1 | $0.01 |
| `tlsrpt` | 1 | $0.01 | `security_headers` | 1 | $0.01 |
| `mx` | 1 | $0.01 | | | |
| `spoofable` | 1 | $0.01 | | | |

Credits per call are set by Lookproof (`x-credits` in [the API description](https://api.lookproof.dev/openapi.json)); requests that fail validation or fail on Lookproof's side use none. With an API key, tool descriptions say "Uses your Lookproof credits." With x402, every tool description states its USDC price, so the agent can see what a call costs before making it.

`get_spending` is free. With an API key it shows your plan and the credits used and left this period (from `GET /v1/usage`); with x402 it shows what the session has spent and how much budget is left.

## Endpoints without a tool

Lookproof has 47 paid endpoints. This server exposes the 23 an agent is most likely to need for questions about a domain's DNS and mail security, because every extra tool costs context and makes the agent's choice harder. The other 24, and why they are left out:

| Endpoints | Why left out |
|---|---|
| `POST /v1/mail/check/bulk` | Up to 20 domains in one paid call ($0.024 each, up to $0.48): too easy for an agent to spend the session budget at once. Use it from a script. |
| `GET /v1/dns/soa`, `/v1/dns/ttl`, `/v1/dns/wildcard`, `/v1/dns/https-rr`, `/v1/dns/compare`, `/v1/dns/ns-provider`, `/v1/dns/txt-verification`, `/v1/mail/ptr` | Specialised DNS diagnostics. `domain_health` (which includes reverse DNS of the mail servers) and `dns_lookup` answer the common questions. |
| `GET /v1/ip/info`, `/v1/ip/cidr`, `/v1/ip/subnets`, `/v1/ip/range-to-cidr`, `POST /v1/ip/contains`, `GET /v1/dns/idn` | Offline IP arithmetic and IDN conversion. An agent can do this itself without paying. |
| `POST /v1/dns/zone-lint`, `/v1/tls/pem-decode`, `/v1/tls/csr-decode`, `/v1/http/csp-parse`, `/v1/http/hsts-parse`, `/v1/http/cookie-parse`, `/v1/mail/mta-sts-parse`, `/v1/mail/bimi-parse`, `/v1/mail/tlsrpt-parse` | Parsers for text the user pastes. They fit a script better than an agent session, and pasted cookies or zone files can contain data the user may not want to send. `spf_parse` and `dmarc_parse` are included as examples of this kind of tool. |

All of them are in [`docs/endpoints.md`](https://github.com/lookproof/x402-examples/blob/master/docs/endpoints.md). To add one, copy a tool in `src/lookproof_mcp/server.py`, set its path and price, and run `uv run lookproof-mcp --check`.

## Option 1: API key

Get a free key with 250 credits a month at [lookproof.dev/pricing](https://lookproof.dev/pricing). Keys start with `lp_`.

The server runs with [uv](https://docs.astral.sh/uv/)'s `uvx`, which downloads `lookproof-mcp` from PyPI into its own environment, with exactly the dependency versions this release was tested with. There is nothing to clone or install by hand.

### Claude Code

```bash
claude mcp add lookproof --env LOOKPROOF_API_KEY=lp_live_your_key -- uvx lookproof-mcp
```

Then ask, for example: *"Is example.com protected against email spoofing? Check SPF, DMARC and MTA-STS."*

### Claude Desktop

Add this to `claude_desktop_config.json` (Settings, Developer, Edit Config) and restart Claude Desktop:

```json
{
  "mcpServers": {
    "lookproof": {
      "command": "uvx",
      "args": ["lookproof-mcp"],
      "env": {
        "LOOKPROOF_API_KEY": "lp_live_your_key"
      }
    }
  }
}
```

If Claude Desktop can't find `uvx`, use its full path (`which uvx` on macOS and Linux, `where uvx` on Windows).

With a key, the plan's credits are the limit: when they are used up, calls return an error (HTTP 429) until the next period or an upgrade. `MAX_SPEND_USD` and the other x402 settings do not apply. Don't set `X402_PAY=1` together with a key; the server refuses to start with both.

## Option 2: x402 (USDC on Base)

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.

Store the wallet key in a file only you can read, so it never sits in an MCP client's config file:

```bash
install -m 600 /dev/null ~/.lookproof-wallet.key
nano ~/.lookproof-wallet.key        # paste the private key, save
```

Try it without a wallet first: with no settings, every tool is a dry run.

### Claude Code

```bash
claude mcp add lookproof \
  --env X402_PAY=1 \
  --env PRIVATE_KEY_FILE=$HOME/.lookproof-wallet.key \
  --env MAX_SPEND_USD=0.25 \
  -- uvx lookproof-mcp
```

Leave out `--env X402_PAY=1` to try it as a dry run first.

### Claude Desktop

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

On Windows, write the key path as `C:\\Users\\you\\.lookproof-wallet.key`.

## Settings

| Variable | Default | Effect |
|---|---|---|
| `LOOKPROOF_API_KEY` | | API key (`lp_...`). When set, every call uses your plan's credits and no wallet is used. |
| `X402_PAY` | off | x402 only. Without `X402_PAY=1` (and without `LOOKPROOF_API_KEY`), every tool runs as a dry run: it reports the price and returns no data. |
| `PRIVATE_KEY_FILE` | | x402 only. Path to a file with the wallet's private key (recommended). It must not be readable by other users. |
| `PRIVATE_KEY` | | x402 only. The key itself, if you prefer an environment variable. |
| `PAYTO_ALLOWLIST` | empty | x402 only. Optional comma-separated addresses; a 402 asking for payment to any other address is refused before signing. See [pinning the receiving address](https://github.com/lookproof/x402-examples#pinning-the-receiving-address-payto_allowlist). |
| `MAX_SPEND_USD` | `0.10` | x402 only. Spending cap for the session (one server process). Calls beyond it are refused, not paid. |

How payments are limited is described under [Security](#security).

## What a tool call returns

With an API key (`data` is the full Lookproof response; the credit counts come from the `X-Quota-Remaining` and `X-Quota-Limit` headers):

```json
{
  "data": {"endpoint": "mail.dmarc", "status": "<ok|info|warning|error|unknown>", "data": {"policy": "...", "...": "..."}, "findings": ["..."]},
  "credits_remaining": 241,
  "credits_limit": 250
}
```

`get_spending` with an API key:

```json
{"mode": "api_key", "calls_this_session": 9, "plan": "free", "period_start": "2026-11-01T00:00:00Z",
 "period_end": "2026-12-01T00:00:00Z", "credits_limit": 250, "credits_used": 9, "credits_remaining": 241,
 "by_endpoint": [{"...": "..."}]}
```

Paid with x402 (shape only, not yet verified against the live API; `data` is the full Lookproof response):

```json
{
  "data": {"endpoint": "mail.dmarc", "status": "<ok|info|warning|error|unknown>", "data": {"policy": "...", "...": "..."}, "findings": ["..."]},
  "cost_usd": 0.01,
  "session_spent_usd": 0.01,
  "session_remaining_usd": 0.09,
  "tx": "https://basescan.org/tx/0x<transaction-hash>"
}
```

Dry run (neither `LOOKPROOF_API_KEY` nor `X402_PAY=1`):

```json
{"dry_run": true, "would_cost_usd": 0.08, "network": "eip155:8453", "pay_to": "0x<lookproof-address>",
 "note": "Dry run, nothing paid and no data. The user can set LOOKPROOF_API_KEY (...) or X402_PAY=1 ..."}
```

When the x402 session cap is reached:

```json
{"error": "Session spending cap reached: $0.090 spent of MAX_SPEND_USD=$0.1; this call costs $0.080. Restart the server or raise MAX_SPEND_USD."}
```

## Security

- **API key.** Keep the key in the MCP client's config or environment, not in prompts. The server sends it only to the Lookproof API as `Authorization: Bearer` and never puts it in a tool result. It refuses a value that does not start with `lp_`, because Lookproof would ignore it and answer with a payment request instead. The plan's credits are the limit, and a failed check uses none.
- **Dedicated wallet.** Use a wallet that only holds what you are willing to spend on checks, never your main wallet. Prefer `PRIVATE_KEY_FILE` over `PRIVATE_KEY`, so the key is not in the MCP client's config file; the server refuses a key file that other users can read.
- **Dry run by default.** Nothing is charged unless `LOOKPROOF_API_KEY` or `X402_PAY=1` is set, and with an API key nothing is ever signed.
- **Spending cap.** `MAX_SPEND_USD` (default $0.10) caps what one server process can spend. The cost of a call is reserved before paying, so parallel calls cannot overshoot it, and a call that fails after the payment was signed stays counted and is reported as "possibly paid".
- **Price check.** A tool refuses to pay more than the price in its description.
- **Locked payment.** Each payment is locked to the amount, asset (USDC), network (Base, `eip155:8453`) and `payTo` address of the 402 the server just received for that call. If the second 402 asks for anything else, nothing is signed. With `PAYTO_ALLOWLIST`, a `payTo` outside the list is refused before signing.
- **Results are data.** Tool results contain records and web content published by the checked domain's owner. The agent is told to treat them as data, and the cap and price checks apply whatever it is told.
- **Identifiable client.** Every request carries `User-Agent: lookproof-mcp/<version>`.

## Command line

| Command | Effect |
|---|---|
| `uvx lookproof-mcp` | Runs the MCP server on stdio (what Claude Code and Claude Desktop start). |
| `uvx lookproof-mcp --check` | Compares every tool's advertised x402 price with the live 402 response. Pays nothing and needs no wallet or key. |
| `uvx lookproof-mcp --version` | Prints the version. |

## Docker

The `Dockerfile` in this directory runs the server on stdio as a dry run. The image contains no key, wallet or other secret; it is what automated checks such as [Glama](https://glama.ai/mcp/servers)'s use to start the server and list its tools.

```bash
docker build -t lookproof-mcp https://github.com/lookproof/x402-examples.git#master:mcp-server
docker run -i --rm -e LOOKPROOF_API_KEY lookproof-mcp      # with the key from your environment
```

Pass secrets at run time with `-e`, never as build arguments.

## Run from source

```bash
git clone https://github.com/lookproof/x402-examples.git
cd x402-examples/mcp-server
uv run lookproof-mcp            # or: uv run lookproof-mcp --check
```

Source, issues and the other x402 examples (quickstart, domain monitor): [github.com/lookproof/x402-examples](https://github.com/lookproof/x402-examples).
