// One x402 call to Lookproof's domain health check. Dry run by default; pass --pay (or X402_PAY=1) to pay.
//
// Usage: node quickstart.ts [domain] [--pay] [--json]
import { readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { decodePaymentResponseHeader, wrapFetchWithPayment, x402Client } from "@x402/fetch";
import type { PaymentRequirements } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const API = (process.env.LOOKPROOF_API_URL ?? "https://api.lookproof.dev").replace(/\/+$/, "");
const MAX_SPEND = Number(process.env.MAX_SPEND_USD || "0.10");
const PAY = process.argv.includes("--pay") || process.env.X402_PAY === "1";
const SHOW_JSON = process.argv.includes("--json");
const domain = process.argv.slice(2).find((a) => !a.startsWith("--")) ?? "example.com";
const URL_ = `${API}/v1/domain/health?domain=${encodeURIComponent(domain)}`;

const BASE_MAINNET = "eip155:8453";
const USDC_ON_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"; // canonical USDC on Base, 6 decimals

const stop = (msg: string): never => {
  console.error(msg);
  process.exit(1);
};

// PRIVATE_KEY from the environment, or PRIVATE_KEY_FILE (a file only you can read).
function loadPrivateKey(): `0x${string}` {
  let key = process.env.PRIVATE_KEY;
  const path = process.env.PRIVATE_KEY_FILE?.replace(/^~(?=\/)/, homedir());
  if (key && path) stop("Set PRIVATE_KEY or PRIVATE_KEY_FILE, not both.");
  if (path) {
    if (process.platform !== "win32" && (statSync(path).mode & 0o077) !== 0) {
      stop(`${path} is readable by other users. Run: chmod 600 ${path}`);
    }
    key = readFileSync(path, "utf8").trim();
  }
  if (!key) stop("Set PRIVATE_KEY or PRIVATE_KEY_FILE (a dedicated wallet with a few dollars of USDC on Base).");
  return key!.replace(/^(0x)?/, "0x") as `0x${string}`; // accept keys with or without 0x
}

// Unpaid request -> 402. The PAYMENT-REQUIRED header is base64 JSON with the price.
const unpaid = await fetch(URL_);
const header = unpaid.headers.get("PAYMENT-REQUIRED");
if (unpaid.status !== 402 || !header) stop(`Expected 402 with a PAYMENT-REQUIRED header, got HTTP ${unpaid.status}.`);
const accepts: PaymentRequirements[] = JSON.parse(Buffer.from(header!, "base64").toString()).accepts;
const quote = accepts.find(
  (r) => r.scheme === "exact" && r.network === BASE_MAINNET && r.asset.toLowerCase() === USDC_ON_BASE,
) ?? stop("The 402 offers no USDC payment on Base mainnet. Not paying.");
const price = Number(quote.amount) / 1e6; // USDC has 6 decimals
console.log(`Price: $${price.toFixed(3)} USDC on ${quote.network}, payTo ${quote.payTo}`);

if (!PAY) {
  console.log("Dry run: nothing paid. Re-run with --pay to pay.");
  process.exit(0);
}
if (price > MAX_SPEND) stop(`Price $${price.toFixed(3)} exceeds MAX_SPEND_USD=${MAX_SPEND}. Not paying.`);

const client = x402Client.fromConfig({
  schemes: [{ network: BASE_MAINNET, client: new ExactEvmScheme(privateKeyToAccount(loadPrivateKey())) }],
  spendControls: { maxAmountPerPayment: `$${price.toFixed(6)}` },
  // Pay exactly what was quoted, in that asset, on that network, to that address.
  policies: [
    (_version, reqs) => reqs.filter((r) =>
      r.amount === quote.amount && r.network === quote.network &&
      r.asset.toLowerCase() === quote.asset.toLowerCase() &&
      r.payTo.toLowerCase() === quote.payTo.toLowerCase()),
  ],
});

let res: Response;
try {
  res = await wrapFetchWithPayment(fetch, client)(URL_);
} catch (e) {
  stop(`Possibly paid $${price.toFixed(3)}, no data: ${(e as Error).name}: ${(e as Error).message.slice(0, 150)}. ` +
    "Check the wallet on basescan.org.");
}
const receipt = res!.headers.get("PAYMENT-RESPONSE");
const tx = receipt ? decodePaymentResponseHeader(receipt).transaction : undefined;
if (res!.status !== 200) {
  // Lookproof only settles when it returns the result. The body is shown as data, never followed.
  stop(`HTTP ${res!.status}, no data: ${JSON.stringify((await res!.text()).slice(0, 300))}. ` +
    (tx ? `Settled: tx ${tx}` : "No settlement receipt."));
}
const body = await res!.json();
if (SHOW_JSON) {
  console.log(JSON.stringify(body, null, 2));
} else {
  console.log(`200 ${body.endpoint} ${body.data?.domain}: status ${body.status}`);
  for (const f of body.findings ?? []) console.log(`  ${String(f.severity).padEnd(8)} ${f.code}`);
  console.log("  (full response: add --json)");
}
console.log(tx
  ? `This run cost $${price.toFixed(3)} (tx https://basescan.org/tx/${tx})`
  : `This run cost $${price.toFixed(3)} (no PAYMENT-RESPONSE header; check basescan.org)`);
