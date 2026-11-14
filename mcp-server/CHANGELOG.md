# Changelog

## 0.2.0 (unreleased)

- API-key mode: with `LOOKPROOF_API_KEY` set, every tool calls Lookproof with `Authorization: Bearer` and uses the credits of your plan instead of paying with x402. No wallet is needed. Tool descriptions say "Uses your Lookproof credits." and results carry `credits_remaining` and `credits_limit` from the `X-Quota-*` headers.
- `get_spending` reports the plan, the period and the credits used and left (from `GET /v1/usage`) in API-key mode, and gains a `mode` field (`api_key` or `x402`) in both modes.
- The server refuses to start with a `LOOKPROOF_API_KEY` that does not start with `lp_`, or with both `LOOKPROOF_API_KEY` and `X402_PAY=1`.
- The dry-run note names both ways to get data: a free API key or `X402_PAY=1`.
- `Dockerfile` that runs the server as a dry run, with no key, wallet or other secret, for automated checks such as Glama's.
- `server.json`: `websiteUrl` is now https://lookproof.dev/agents, the setup page for MCP clients.
- x402 mode is unchanged.

## 0.1.0

First packaged release as `lookproof-mcp`, runnable with `uvx lookproof-mcp`.

- 23 paid tools plus the free `get_spending`, the same as the `mcp-server/server.py` example it replaces.
- CLI: `--version`, `--check` (compare advertised prices with the live 402 responses, pays nothing) and the default stdio server.
- Requests identify themselves with `User-Agent: lookproof-mcp/<version>`.
