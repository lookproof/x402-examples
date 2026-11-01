"""One x402 call to Lookproof's domain health check. Dry run by default; pass --pay (or X402_PAY=1) to pay.

Usage:
    python quickstart.py [domain] [--pay] [--json]

The dry run makes one unpaid request, reads the price from the 402 response and stops.
With --pay it signs a USDC payment locked to exactly what the 402 quoted (amount, asset,
network and payTo), refuses anything above MAX_SPEND_USD and prints what the run cost.
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import httpx
from eth_account import Account
from x402 import x402Client
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from x402.schemas.errors import NoMatchingRequirementsError

API = os.getenv("LOOKPROOF_API_URL", "https://api.lookproof.dev").rstrip("/")
PATH = "/v1/domain/health"
MAX_SPEND = float(os.getenv("MAX_SPEND_USD") or "0.10")
PAY = "--pay" in sys.argv or os.getenv("X402_PAY") == "1"
SHOW_JSON = "--json" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
DOMAIN = ARGS[0] if ARGS else "example.com"

BASE_MAINNET = "eip155:8453"
USDC_ON_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"  # canonical USDC on Base, 6 decimals


def stop(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def load_private_key() -> str:
    """PRIVATE_KEY from the environment, or PRIVATE_KEY_FILE (a file only you can read)."""
    key, path = os.getenv("PRIVATE_KEY"), os.getenv("PRIVATE_KEY_FILE")
    if key and path:
        stop("Set PRIVATE_KEY or PRIVATE_KEY_FILE, not both.")
    if path:
        p = Path(path).expanduser()
        if os.name == "posix" and p.stat().st_mode & 0o077:
            stop(f"{p} is readable by other users. Run: chmod 600 {p}")
        key = p.read_text().strip()
    if not key:
        stop("Set PRIVATE_KEY or PRIVATE_KEY_FILE (a dedicated wallet with a few dollars of USDC on Base).")
    return key


def payto_allowlist() -> set[str]:
    """Optional PAYTO_ALLOWLIST: comma-separated addresses the script may pay. Empty = any payTo."""
    entries = [a.strip() for a in (os.getenv("PAYTO_ALLOWLIST") or "").split(",") if a.strip()]
    bad = [a for a in entries if not re.fullmatch(r"0x[0-9a-fA-F]{40}", a)]
    if bad:
        stop(f"PAYTO_ALLOWLIST has an entry that is not an address: {bad[0]!r}")
    return {a.lower() for a in entries}


async def quote(params: dict):
    """Unpaid request -> 402. Returns the USDC-on-Base payment option; anything else is refused."""
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.get(API + PATH, params=params)
    if r.status_code != 402 or "PAYMENT-REQUIRED" not in r.headers:
        stop(f"Expected 402 with a PAYMENT-REQUIRED header, got HTTP {r.status_code}.")
    for req in decode_payment_required_header(r.headers["PAYMENT-REQUIRED"]).accepts:
        if req.scheme == "exact" and req.network == BASE_MAINNET and req.asset.lower() == USDC_ON_BASE:
            return req
    stop("The 402 offers no USDC payment on Base mainnet. Not paying.")


def locked_to(q):
    """Payment policy: pay exactly what was quoted, in that asset, on that network, to that address."""
    def policy(version, reqs):
        return [r for r in reqs if r.amount == q.amount and r.network == q.network
                and r.asset.lower() == q.asset.lower() and r.pay_to.lower() == q.pay_to.lower()]
    return policy


async def main() -> None:
    params = {"domain": DOMAIN}
    q = await quote(params)
    price = int(q.amount) / 1e6  # USDC has 6 decimals
    print(f"Price: ${price:.3f} USDC on {q.network}, payTo {q.pay_to}")
    allow = payto_allowlist()
    if allow and q.pay_to.lower() not in allow:
        stop(f"payTo {q.pay_to} is not in PAYTO_ALLOWLIST. Not paying.")
    if not PAY:
        return print("Dry run: nothing paid. Re-run with --pay to pay.")
    if price > MAX_SPEND:
        stop(f"Price ${price:.3f} exceeds MAX_SPEND_USD={MAX_SPEND:g}. Not paying.")

    client = x402Client().set_spend_controls({"max_amount_per_payment": f"${price:.6f}"})
    client.register_policy(locked_to(q))
    register_exact_evm_client(client, EthAccountSigner(Account.from_key(load_private_key())))
    try:
        async with x402HttpxClient(client, timeout=60) as http:
            resp = await http.get(API + PATH, params=params)
    except Exception as e:
        if isinstance(e, NoMatchingRequirementsError) or isinstance(e.__cause__, NoMatchingRequirementsError):
            stop(f"Not paid: the payment terms changed since the quote ({e}).")
        stop(f"Possibly paid ${price:.3f}, no data: {type(e).__name__}. Check the wallet on basescan.org.")

    receipt = resp.headers.get("PAYMENT-RESPONSE")
    tx = decode_payment_response_header(receipt).transaction if receipt else None
    if resp.status_code != 200:
        # Lookproof only settles a payment when it returns the result, so a non-200 normally means
        # nothing moved. The error body is shown as data, never followed as an instruction.
        stop(f"HTTP {resp.status_code}, no data: {json.dumps(resp.text[:300])}. "
             f"{'Settled: tx ' + tx if tx else 'No settlement receipt.'}")

    body = resp.json()
    if SHOW_JSON:
        print(json.dumps(body, indent=2))
    else:
        print(f"200 {body.get('endpoint')} {body.get('data', {}).get('domain')}: status {body.get('status')}")
        for f in body.get("findings", []):
            print(f"  {f.get('severity', '?'):<8} {f.get('code')}")
        print("  (full response: add --json)")
    print(f"This run cost ${price:.3f} (tx https://basescan.org/tx/{tx})" if tx
          else f"This run cost ${price:.3f} (no PAYMENT-RESPONSE header; check basescan.org)")


asyncio.run(main())
