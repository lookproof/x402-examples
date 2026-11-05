# Changelog

## 0.1.0 (unreleased)

First packaged release as `lookproof-mcp`, runnable with `uvx lookproof-mcp`.

- 23 paid tools plus the free `get_spending`, the same as the `mcp-server/server.py` example it replaces.
- CLI: `--version`, `--check` (compare advertised prices with the live 402 responses, pays nothing) and the default stdio server.
- Requests identify themselves with `User-Agent: lookproof-mcp/<version>`.
