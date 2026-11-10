# Lookproof x402 examples

[Lookproof](https://lookproof.dev)'s API runs DNS and email security checks (SPF, DKIM, DMARC, MTA-STS, DNSSEC, TLS, HTTP headers and more) per call, paid in USDC on Base with the [x402 protocol](https://x402.org). No account, no API key: the payment is the credential.

These examples get you from zero to a paid check in a few minutes, and show how agents and scripts can build on it.

## Examples

| Example | Language | What it does | Cost per run |
|---|---|---|---|
| [quickstart](quickstart/) | Python, TypeScript | One paid call to the domain health check (`/v1/domain/health`) | $0.08 |
| [domain-monitor](domain-monitor/) | Python | Checks a list of domains daily and alerts (stdout, Discord, Telegram, email) when SPF, DKIM, DMARC or MTA-STS changes or gets weaker | $0.08 per domain |
| [mcp-server](mcp-server/) | Python | 24 Lookproof checks as MCP tools for Claude and other AI agents, paid per call with a session cap. Installs with `uvx lookproof-mcp` | $0.002-0.08 per tool call |

All 48 paid endpoints with prices, inputs and example responses: [docs/endpoints.md](docs/endpoints.md). Prices range from $0.002 to $0.08 per call.

## Quickstart

You need a dedicated wallet with a few dollars of USDC on Base mainnet (see [Security](#security)).

```bash
git clone https://github.com/lookproof/x402-examples.git
cd x402-examples/quickstart/python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python quickstart.py example.com          # dry run: shows the price, pays nothing

install -m 600 /dev/null ~/.lookproof-wallet.key     # a key file only you can read
nano ~/.lookproof-wallet.key                         # paste the wallet's private key, save
export PRIVATE_KEY_FILE=~/.lookproof-wallet.key
.venv/bin/python quickstart.py example.com --pay    # pays $0.08
```

Shape of the paid call's output (not yet verified against the live API; values in `<>` vary):

```
Price: $0.080 USDC on eip155:8453, payTo 0x<lookproof-address>
200 domain.health example.com: status <ok|info|warning|error|unknown>
  <severity> <FINDING_CODE>
  (full response: add --json)
This run cost $0.080 (tx https://basescan.org/tx/0x<transaction-hash>)
```

The TypeScript version and a minimal snippet are in [quickstart/](quickstart/).

## How x402 works

1. You call an endpoint without paying and get `402 Payment Required`, with the price, network and receiving address in the `PAYMENT-REQUIRED` header.
2. Your x402 client signs a USDC transfer authorization (EIP-3009) for exactly that amount.
3. You send the same request again with the signature. Lookproof runs the check, a facilitator settles the payment on Base, and you get `200` with the result and the transaction hash in the `PAYMENT-RESPONSE` header.

Lookproof settles only when it returns a result: a check that fails (`503`) is not charged. The official x402 client libraries ([Python](https://pypi.org/project/x402/), [TypeScript](https://www.npmjs.com/package/@x402/fetch)) do steps 2 and 3 for you.

## Security

- **Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.** The facilitator pays the gas, so the wallet only needs USDC. Lookproof accepts signatures from ordinary wallets (EOA), not smart-contract wallets.
- **Keep the key out of the repository.** Put it in a file only you can read (`chmod 600`) and point `PRIVATE_KEY_FILE` at it, or set `PRIVATE_KEY` in your environment. The examples refuse a key file that other users can read. [.env.example](.env.example) lists every setting with placeholders; `.env` is ignored by git.
- **Dry run by default.** Every example shows what it would pay and stops. It only pays with `--pay` or `X402_PAY=1`.
- **Spending cap.** Every example refuses to spend more than `MAX_SPEND_USD` per run (the MCP server: per session), default $0.10, and prints what the run cost.
- **Locked payments.** Each payment is locked to the exact amount, asset (USDC), network (Base, `eip155:8453`) and `payTo` address of the 402 response for that request. If the terms change between the quote and the payment, nothing is signed.
- **Optional payTo allowlist.** Set `PAYTO_ALLOWLIST` to only ever pay addresses you have checked yourself (see below).
- **API responses are data.** DNS records, policies and web pages are published by whoever owns the checked domain. The examples compare and display them, and never follow them as instructions. The MCP server tells the agent the same.

### Pinning the receiving address (`PAYTO_ALLOWLIST`)

By default the examples pay the `payTo` address that the 402 response names, after checking network, asset and price. That protects you against overpaying, but not against a 402 that names a different address, for example if a proxy, a DNS hijack or a compromised server answers instead of Lookproof.

If you want that protection too, pin the address:

1. Run any example as a dry run. It prints the `payTo` address from the 402.
2. Check that address against a source you trust, such as [lookproof.dev](https://lookproof.dev) or earlier payments in your wallet on [basescan.org](https://basescan.org).
3. Set it in your environment or `.env` (several addresses are comma-separated):

```bash
export PAYTO_ALLOWLIST=0x<lookproof-address>
```

From then on every example refuses, before signing anything, a 402 that asks for payment to any other address. The dry run reports the same refusal, so you can test the setting without paying. If Lookproof ever changes its receiving address, the examples stop paying until you add the new one. The address is deliberately not hardcoded in this repository: you decide which address to trust.

## Tests

The tests run every example against a local fake of the API (`tests/fake_lookproof.py`) with a throwaway key. Nothing touches a chain and no money moves.

```bash
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
(cd quickstart/typescript && npm install)   # optional, for the TypeScript test
.venv/bin/python -m pytest tests
```

## Links

- Lookproof: [lookproof.dev](https://lookproof.dev)
- API base URL: `https://api.lookproof.dev` (OpenAPI document at [/openapi.json](https://api.lookproof.dev/openapi.json))
- x402 protocol: [x402.org](https://x402.org)

## License

[MIT](LICENSE)
