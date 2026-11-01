# Lookproof MCP server

An [MCP](https://modelcontextprotocol.io) server that gives Claude and other AI agents 23 Lookproof tools: domain and site health, SPF, DKIM, DMARC, MTA-STS, BIMI, DNS, DNSSEC, CAA, RDAP, TLS certificates and HTTP security headers. The agent pays per call in USDC on Base via x402, from a wallet you control, with a spending cap per session.

Every tool description states its price, so the agent can see what a call costs before making it.

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

`get_spending` is free and shows what the session has spent and how much budget is left. The other 24 endpoints (IP tools, zone lint, certificate and header parsers, bulk mail checks) are in [`../docs/endpoints.md`](../docs/endpoints.md); add a tool for one with a few lines in `server.py`.

## Setup

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.

```bash
cd mcp-server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Store the wallet key in a file only you can read, so it never sits in a config file:
install -m 600 /dev/null ~/.lookproof-wallet.key
nano ~/.lookproof-wallet.key        # paste the private key, save
```

## Settings

| Variable | Default | Effect |
|---|---|---|
| `X402_PAY` | off | Without `X402_PAY=1`, every tool runs as a dry run: it reports the price and returns no data. |
| `PRIVATE_KEY_FILE` | | Path to a file with the wallet's private key (recommended). It must not be readable by other users. |
| `PRIVATE_KEY` | | The key itself, if you prefer an environment variable. |
| `MAX_SPEND_USD` | `0.10` | Spending cap for the session (one server process). Calls beyond it are refused, not paid. |

Each payment is locked to the price, asset (USDC), network (Base, `eip155:8453`) and `payTo` address the API quoted for that call, and a tool refuses to pay more than the price in its description. If a call fails after the payment was signed, it still counts against the cap and is reported as "possibly paid".

Tool results contain DNS records, policies and web content published by whoever owns the checked domain. The server's instructions tell the agent to treat them as data, never as instructions, and the spending cap and price checks apply whatever the agent is told.

## Claude Code

```bash
claude mcp add lookproof \
  --env X402_PAY=1 \
  --env PRIVATE_KEY_FILE=$HOME/.lookproof-wallet.key \
  --env MAX_SPEND_USD=0.25 \
  -- /path/to/x402-examples/mcp-server/.venv/bin/python /path/to/x402-examples/mcp-server/server.py
```

Then ask, for example: *"Is example.com protected against email spoofing? Check SPF, DMARC and MTA-STS."*

## Claude Desktop

Add this to `claude_desktop_config.json` (Settings, Developer, Edit Config) and restart Claude Desktop:

```json
{
  "mcpServers": {
    "lookproof": {
      "command": "/path/to/x402-examples/mcp-server/.venv/bin/python",
      "args": ["/path/to/x402-examples/mcp-server/server.py"],
      "env": {
        "X402_PAY": "1",
        "PRIVATE_KEY_FILE": "/home/you/.lookproof-wallet.key",
        "MAX_SPEND_USD": "0.25"
      }
    }
  }
}
```

On Windows, use `.venv\\Scripts\\python.exe` and Windows paths.

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

## For maintainers

`python server.py --check` compares every tool's advertised price with the live API. It pays nothing.
