# Changelog

## 0.1.0 (unreleased)

First packaged release as `lookproof-mcp`, runnable with `uvx lookproof-mcp`.

- 24 paid tools plus the free `get_spending`: the 23 of the `mcp-server/server.py` example it replaces, and `x402_check` (`GET /v1/http/x402`, $0.01), which checks an x402 endpoint before an agent pays it.
- CLI: `--version`, `--check` (compare advertised prices with the live 402 responses, pays nothing) and the default stdio server.
- Requests identify themselves with `User-Agent: lookproof-mcp/<version>`.
