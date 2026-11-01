"""Regenerate docs/endpoints.md and docs/endpoints.json from Lookproof's OpenAPI document.

Lookproof generates its OpenAPI document from the endpoint registry in the API repository
(probekit_contracts.openapi.render_openapi), and https://api.lookproof.dev/openapi.json serves
exactly those bytes. Pick one source:

    python3 scripts/gen_endpoints.py --live                       # fetch the published document
    python3 scripts/gen_endpoints.py --openapi path/to/openapi.json
    python3 scripts/gen_endpoints.py --repo /path/to/lookproof    # render from the registry (needs uv)

Only paid x402 operations are listed. Free operations (bulk retry, /v1/usage) are mentioned
in the header. Example responses come from the registry and are illustrative (example.com).
"""
import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_URL = "https://api.lookproof.dev/openapi.json"
RENDER = (
    "import sys\n"
    "from probekit_contracts.catalog import REGISTRY\n"
    "from probekit_contracts.openapi import render_openapi\n"
    "sys.stdout.buffer.write(render_openapi(REGISTRY, base_url='https://lookproof.dev', "
    "api_base_url='https://api.lookproof.dev', network='eip155:8453'))\n"
)
NETWORK_NAMES = {"eip155:8453": "Base", "eip155:84532": "Base Sepolia (testnet)"}
CATEGORY_ORDER = ["domain", "site", "mail", "dns", "tls", "http", "ip"]
CATEGORY_TITLES = {"domain": "Domain", "site": "Site", "mail": "Mail", "dns": "DNS", "tls": "TLS",
                   "http": "HTTP", "ip": "IP"}


def load(args) -> tuple[dict, str]:
    if args.openapi:
        return json.loads(Path(args.openapi).read_text()), f"`{Path(args.openapi).name}`"
    if args.repo:
        out = subprocess.run(["uv", "run", "--directory", args.repo, "python", "-c", RENDER],
                             check=True, capture_output=True)
        rev = subprocess.run(["git", "-C", args.repo, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        return json.loads(out.stdout), f"the Lookproof endpoint registry (commit `{rev}`)"
    req = urllib.request.Request(LIVE_URL, headers={"User-Agent": "lookproof-x402-examples/gen_endpoints"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()), f"`{LIVE_URL}`"


def price_text(rule: dict) -> str:
    if rule["kind"] == "fixed":
        return f"${rule['amount'] / 1e6:g}"
    if rule["kind"] == "per_item":
        return (f"${rule['per_item'] / 1e6:g} per domain, min ${rule['minimum'] / 1e6:g}, "
                f"max {rule['max_items']} domains")
    raise ValueError(f"unknown price rule {rule['kind']!r}")


def trim(v, depth=0):
    """Shorten long examples: first list item only, long strings cut."""
    if isinstance(v, dict):
        return {k: trim(x, depth + 1) for k, x in v.items()}
    if isinstance(v, list):
        return [trim(x, depth + 1) for x in v[:1]] + (["..."] if len(v) > 1 else [])
    if isinstance(v, str) and len(v) > 90:
        return v[:87] + "..."
    return v


def operations(doc: dict) -> list[dict]:
    ops = []
    for path, methods in doc["paths"].items():
        for method, op in methods.items():
            if "x-price" not in op:
                continue  # free operation
            params = [p for p in op.get("parameters", []) if "name" in p]
            body = op.get("requestBody", {}).get("content", {}).get("application/json", {})
            ok = op["responses"]["200"]["content"]["application/json"]
            ops.append({
                "id": op["operationId"],
                "category": path.split("/")[2],
                "method": method.upper(),
                "path": path,
                "summary": op["summary"],
                "description": op["description"],
                "price": op["x-price"]["rule"],
                "price_text": price_text(op["x-price"]["rule"]),
                "params": [{"name": p["name"], "required": bool(p.get("required")),
                            "example": p.get("example")} for p in params],
                "body_example": body.get("example"),
                "body_fields": sorted(body.get("schema", {}).get("properties", {})),
                "example_response": ok.get("example"),
                "finding_codes": op.get("x-finding-codes", []),
            })
    rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    return sorted(ops, key=lambda o: (rank.get(o["category"], 99), o["path"]))


def inputs_text(o: dict) -> str:
    if o["method"] == "POST":
        return "JSON body: " + ", ".join(f"`{f}`" for f in o["body_fields"])
    return ", ".join(f"`{p['name']}`" + (" (required)" if p["required"] else "") for p in o["params"]) or "-"


def render_md(doc: dict, ops: list[dict], source: str) -> str:
    pay = next(iter(ops))
    x_payment = doc["paths"][pay["path"]][pay["method"].lower()]["x-payment"]
    fixed = [o["price"]["amount"] for o in ops if o["price"]["kind"] == "fixed"]
    L = ["# Lookproof x402 endpoints", ""]
    L.append(f"Base URL: `{doc['servers'][0]['url']}`. Every operation below answers `402 Payment Required` "
             "(x402 v2) until paid; the `PAYMENT-REQUIRED` header has the exact price. No account and "
             "no API key needed. Responses are JSON.")
    L.append("")
    L.append("| Network | CAIP-2 id | Asset | Scheme |")
    L.append("|---|---|---|---|")
    L.append(f"| {NETWORK_NAMES.get(x_payment['network'], x_payment['network'])} | `{x_payment['network']}` "
             f"| USDC `{x_payment['asset']}` | `{x_payment['scheme']}` |")
    L.append("")
    L.append("Payments are settled only when the check returns a result. A `503` (`check_failed`, "
             "`deadline_exceeded`, `busy`) is not charged. Signatures must come from an ordinary wallet "
             "(EOA); smart-contract wallets are not supported. Limits: 60 requests per minute and "
             "5000 per day per client IP, and at most 2 concurrent paid requests per IP.")
    L.append("")
    L.append("Free: `/openapi.json`, `/healthz`, and `POST /v1/mail/check/bulk/retry` (re-runs the failed "
             "items of a paid bulk request with its `retry_token`). `GET /v1/usage` is for API-key "
             "customers and has no x402 price.")
    L.append("")
    L.append(f"Generated by `scripts/gen_endpoints.py` from {source}. Example responses are the "
             "registry's illustrative examples for `example.com`, trimmed (`...`); they are not live data.")
    L.append("")
    L.append("## Overview")
    L.append("")
    L.append("| Category | Method | Endpoint | Price (USDC) | Inputs |")
    L.append("|---|---|---|---|---|")
    for o in ops:
        L.append(f"| {CATEGORY_TITLES.get(o['category'], o['category'])} | {o['method']} | `{o['path']}` "
                 f"| {o['price_text']} | {inputs_text(o)} |")
    L.append("")
    L.append(f"{len(ops)} paid operations. Fixed prices range from ${min(fixed) / 1e6:g} to "
             f"${max(fixed) / 1e6:g} per call.")
    L.append("")
    L.append("## Details")
    L.append("")
    cur = None
    for o in ops:
        if o["category"] != cur:
            cur = o["category"]
            L += [f"### {CATEGORY_TITLES.get(cur, cur)}", ""]
        L += [f"#### `{o['method']} {o['path']}` ({o['price_text']})", ""]
        L += [f"**{o['summary']}.** {o['description'].replace(chr(10), ' ')}", ""]
        if o["method"] == "GET":
            q = "&".join(f"{p['name']}={v}" for p in o["params"] if p["example"] is not None
                         for v in (p["example"] if isinstance(p["example"], list) else [p["example"]]))
            L += ["Example request:", "", "```", f"GET {o['path']}" + (f"?{q}" if q else ""), "```", ""]
        elif o["body_example"] is not None:
            L += ["Example request:", "", "```", f"POST {o['path']}",
                  json.dumps(trim(o["body_example"]), ensure_ascii=False), "```", ""]
        if o["example_response"] is not None:
            L += ["Example response (illustrative):", "", "```json",
                  json.dumps(trim(o["example_response"]), indent=2, ensure_ascii=False), "```", ""]
    return "\n".join(L).rstrip() + "\n"


def render_json(ops: list[dict]) -> str:
    keep = ("id", "method", "path", "summary", "price", "params", "body_fields", "body_example",
            "example_response")
    return json.dumps([{k: o[k] for k in keep} for o in ops], indent=1, ensure_ascii=False) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--live", action="store_true", help=f"fetch {LIVE_URL}")
    src.add_argument("--openapi", help="path to an openapi.json")
    src.add_argument("--repo", help="path to a lookproof/lookproof checkout (renders with uv)")
    args = ap.parse_args()
    doc, source = load(args)
    ops = operations(doc)
    (ROOT / "docs/endpoints.md").write_text(render_md(doc, ops, source))
    (ROOT / "docs/endpoints.json").write_text(render_json(ops))
    print(f"wrote docs/endpoints.md and docs/endpoints.json: {len(ops)} paid operations", file=sys.stderr)


if __name__ == "__main__":
    main()
