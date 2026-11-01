# Quickstart: your first paid x402 call

One call to Lookproof's domain health check, `/v1/domain/health`, for $0.08 in USDC on Base. It runs MX, SPF, DMARC, DKIM selector discovery, MTA-STS with TLS-RPT, DNSSEC, reverse DNS, BIMI and CAA for one domain. No account and no API key: the payment is the credential.

The paid call itself is only a few lines.

**Python**

```python
import asyncio, os
from eth_account import Account
from x402 import x402Client
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client

async def main():
    client = x402Client()
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(os.environ["PRIVATE_KEY"])))
    async with x402HttpxClient(client, timeout=60) as http:
        r = await http.get("https://api.lookproof.dev/v1/domain/health", params={"domain": "example.com"})
        print(r.json())

asyncio.run(main())
```

**TypeScript**

```typescript
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${string}`);
const fetchWithPayment = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network: "eip155:8453", client: new ExactEvmScheme(account) }],
});
const res = await fetchWithPayment("https://api.lookproof.dev/v1/domain/health?domain=example.com");
console.log(await res.json());
```

These snippets pay whatever the API asks, up to the x402 client's default limit of $1 per payment. The full quickstart adds a dry run, a spending cap, a payment locked to the quoted terms and a cost report:
[`python/quickstart.py`](python/quickstart.py) and [`typescript/quickstart.ts`](typescript/quickstart.ts).

## Before you start

Use a dedicated wallet with a few dollars of USDC on Base mainnet. Never your main wallet.
The facilitator pays the gas, so the wallet only needs USDC.

Store the key in a file only you can read, so it never sits in your shell history:

```bash
install -m 600 /dev/null ~/.lookproof-wallet.key
nano ~/.lookproof-wallet.key        # paste the private key, save
export PRIVATE_KEY_FILE=~/.lookproof-wallet.key
```

`PRIVATE_KEY=0x...` in the environment works too. The scripts never pay unless you ask them to:

| Setting | Default | Effect |
|---|---|---|
| `--pay` or `X402_PAY=1` | off | Without it, the script only shows the price (dry run). |
| `MAX_SPEND_USD` | `0.10` | The script refuses to pay a price above this. |
| `--json` | off | Print the full JSON response instead of a summary. |

## Python

Requires Python 3.10+.

```bash
cd python
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python quickstart.py example.com          # dry run
.venv/bin/python quickstart.py example.com --pay    # pays $0.08
```

## TypeScript

Requires Node.js 22.18+ (runs `.ts` files directly, no build step).

```bash
cd typescript
npm install
node quickstart.ts example.com          # dry run
node quickstart.ts example.com --pay    # pays $0.08
```

## Expected output

Dry run (both languages; the `payTo` address is Lookproof's receiving wallet from the 402):

```
Price: $0.080 USDC on eip155:8453, payTo 0x<lookproof-address>
Dry run: nothing paid. Re-run with --pay to pay.
```

Paid call (shape only, not yet verified against the live API; values in `<>` vary):

```
Price: $0.080 USDC on eip155:8453, payTo 0x<lookproof-address>
200 domain.health example.com: status <ok|info|warning|error|unknown>
  <severity> <FINDING_CODE>
  (full response: add --json)
This run cost $0.080 (tx https://basescan.org/tx/0x<transaction-hash>)
```

Open the basescan link to see the USDC transfer on-chain. The full response (`--json`) has one section per check (`mx`, `spf`, `dmarc`, `dkim`, `mta_sts`, `dnssec`, `ptr`, `bimi`, `caa`, `provider`) and a list of findings; see [`../docs/endpoints.md`](../docs/endpoints.md#get-v1domainhealth-008) for an example.

## What happens under the hood

1. The script calls the endpoint without payment and gets `402 Payment Required`.
   The `PAYMENT-REQUIRED` header is base64 JSON with the price, network, asset and `payTo` address.
2. The script checks the terms: USDC on Base mainnet, at most `MAX_SPEND_USD`.
3. The x402 client signs a USDC transfer authorization (EIP-3009) for exactly that amount, to exactly that `payTo`. A payment policy refuses to sign if the second 402 differs from the quote.
4. The script sends the request again with the signed payment in the `PAYMENT-SIGNATURE` header.
5. Lookproof runs the check, a facilitator (Coinbase CDP) settles the payment on Base, and the API returns `200` with the result.
   The `PAYMENT-RESPONSE` header contains the transaction hash. A failed check (`503`) is not settled.

All 47 endpoints and their prices: [`../docs/endpoints.md`](../docs/endpoints.md).
