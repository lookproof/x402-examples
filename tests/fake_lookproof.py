"""A local stand-in for api.lookproof.dev, for testing the examples without real money.

It answers like Lookproof's public API: an unpaid request gets 402 with a PAYMENT-REQUIRED
header (x402 v2, USDC on Base, prices from docs/endpoints.json); a request with a
PAYMENT-SIGNATURE gets the documented example response and a PAYMENT-RESPONSE header with a
fake transaction hash. Nothing touches a chain: the signature is decoded and its EIP-712
signer recovered, but nothing is settled. Use a throwaway key with it.

    python tests/fake_lookproof.py [port]        # then LOOKPROOF_API_URL=http://127.0.0.1:<port>

Test knobs (environment):
    FAKE_PRICE_FACTOR   multiply every price (e.g. 2 to test price checks)
    FAKE_PAY_TO         payTo address to quote
    FAKE_SWITCH_PAY_TO  quote this payTo on the second 402 (tests the payment lock)
    FAKE_STATUS         status for paid requests (e.g. 503 to test failures)
    FAKE_DATA_FILE      JSON file: {"<domain>": {<domain.health data>}} served for domain.health
    FAKE_API_KEY        the one valid API key (default lp_test_fake); any other lp_ key gets 401
    FAKE_CREDITS        credits per period for that key (default 250); each successful key request uses 1

A request with Authorization: Bearer lp_... is answered like an API-key customer: no 402, the
example response with X-Quota-* headers, and GET /v1/usage reports the credits.
"""
import base64
import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from eth_account import Account
from eth_account.messages import encode_typed_data
from x402.http import (decode_payment_signature_header, encode_payment_required_header,
                       encode_payment_response_header)
from x402.schemas import PaymentRequired, PaymentRequirements, ResourceInfo, SettleResponse

ROOT = Path(__file__).resolve().parent.parent
ENDPOINTS = {(e["method"], e["path"]): e for e in json.loads((ROOT / "docs/endpoints.json").read_text())}
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
quotes_served = 0
paid_log: list[dict] = []
user_agents: list[str] = []  # User-Agent of every request to an endpoint
key_log: list[dict] = []  # successful API-key requests


def price_atomic(e: dict, body: dict | None) -> int:
    rule = e["price"]
    if rule["kind"] == "fixed":
        return int(rule["amount"] * float(os.getenv("FAKE_PRICE_FACTOR", "1")))
    items = len((body or {}).get("domains", [])) or 1
    return int(max(rule["minimum"], rule["per_item"] * items) * float(os.getenv("FAKE_PRICE_FACTOR", "1")))


def requirements(e: dict, body: dict | None) -> PaymentRequirements:
    global quotes_served
    quotes_served += 1
    pay_to = os.getenv("FAKE_PAY_TO", "0x000000000000000000000000000000000000dEaD")
    if quotes_served > 1 and os.getenv("FAKE_SWITCH_PAY_TO"):
        pay_to = os.environ["FAKE_SWITCH_PAY_TO"]
    return PaymentRequirements(scheme="exact", network="eip155:8453", asset=USDC,
                               amount=str(price_atomic(e, body)), pay_to=pay_to, max_timeout_seconds=60,
                               extra={"name": "USD Coin", "version": "2"})


def recover_signer(payload) -> str:
    auth = payload.payload["authorization"]
    typed = {
        "types": {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                                   {"name": "chainId", "type": "uint256"},
                                   {"name": "verifyingContract", "type": "address"}],
                  "TransferWithAuthorization": [
                      {"name": "from", "type": "address"}, {"name": "to", "type": "address"},
                      {"name": "value", "type": "uint256"}, {"name": "validAfter", "type": "uint256"},
                      {"name": "validBefore", "type": "uint256"}, {"name": "nonce", "type": "bytes32"}]},
        "primaryType": "TransferWithAuthorization",
        "domain": {"name": "USD Coin", "version": "2", "chainId": 8453, "verifyingContract": USDC},
        "message": {"from": auth["from"], "to": auth["to"], "value": int(auth["value"]),
                    "validAfter": int(auth["validAfter"]), "validBefore": int(auth["validBefore"]),
                    "nonce": auth["nonce"]},
    }
    return Account.recover_message(encode_typed_data(full_message=typed), signature=payload.payload["signature"])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, status: int, body: dict, headers: dict | None = None) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _api_key(self) -> str | None:
        auth = self.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Bearer ") else ""
        return token if token.startswith("lp_") else None  # like Lookproof: a non-lp_ value is ignored

    def _quota_headers(self) -> dict:
        limit = int(os.getenv("FAKE_CREDITS", "250"))
        return {"X-Quota-Limit": str(limit), "X-Quota-Remaining": str(max(limit - len(key_log), 0)),
                "X-Quota-Reset": "1767225600"}

    def _handle_key(self, method: str, url, e: dict | None, key: str) -> None:
        if key != os.getenv("FAKE_API_KEY", "lp_test_fake"):
            return self._send(401, {"error": {"code": "invalid_api_key", "message": "unknown key"}})
        if self.headers.get("PAYMENT-SIGNATURE"):
            return self._send(400, {"error": {"code": "bad_request", "message": "key and payment"}})
        limit = int(os.getenv("FAKE_CREDITS", "250"))
        if url.path == "/v1/usage" and method == "GET":
            return self._send(200, {"request_id": "req_fake", "plan": "free", "period_start": "2026-11-01T00:00:00Z",
                                    "period_end": "2026-12-01T00:00:00Z", "credits_limit": limit,
                                    "credits_used": len(key_log), "credits_remaining": max(limit - len(key_log), 0),
                                    "by_endpoint": []}, self._quota_headers())
        if e is None:
            return self._send(404, {"error": {"code": "not_found"}})
        if method == "POST":
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if len(key_log) >= limit:
            return self._send(429, {"error": {"code": "quota_exceeded", "message": "credits used up"}},
                              self._quota_headers())
        key_log.append({"path": url.path})
        self._send(200, e["example_response"], self._quota_headers())

    def _handle(self, method: str) -> None:
        url = urlsplit(self.path)
        if url.path == "/_paid":
            return self._send(200, {"paid": paid_log, "quotes": quotes_served})
        e = ENDPOINTS.get((method, url.path))
        key = self._api_key()
        if key:
            user_agents.append(self.headers.get("User-Agent", ""))
            return self._handle_key(method, url, e, key)
        if e is None:
            return self._send(404, {"error": {"code": "not_found"}})
        user_agents.append(self.headers.get("User-Agent", ""))
        body = None
        if method == "POST":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        req = requirements(e, body)
        sig = self.headers.get("PAYMENT-SIGNATURE")
        if not sig:
            pr = PaymentRequired(x402_version=2, resource=ResourceInfo(url=f"http://fake{self.path}"), accepts=[req])
            return self._send(402, {}, {"PAYMENT-REQUIRED": encode_payment_required_header(pr)})
        payload = decode_payment_signature_header(sig)
        auth = payload.payload["authorization"]
        a = payload.accepted
        if (a.amount != req.amount or a.pay_to.lower() != req.pay_to.lower() or int(auth["value"]) != int(req.amount)
                or auth["to"].lower() != req.pay_to.lower() or recover_signer(payload).lower() != auth["from"].lower()):
            return self._send(402, {"error": "payment_requirements_mismatch"})
        status = int(os.getenv("FAKE_STATUS", "200"))
        if status != 200:
            return self._send(status, {"error": {"code": "check_failed", "message": "fake failure"}})
        paid_log.append({"path": url.path, "amount": req.amount, "from": auth["from"], "to": auth["to"]})
        resp = json.loads(json.dumps(e["example_response"]))
        if e["id"] == "domain.health" and os.getenv("FAKE_DATA_FILE"):
            domain = parse_qs(url.query).get("domain", ["example.com"])[0]
            data = json.loads(Path(os.environ["FAKE_DATA_FILE"]).read_text()).get(domain)
            if data is not None:
                resp["data"] = data.get("data", data)
                resp["findings"] = data.get("findings", [])
        tx = "0x" + hashlib.sha256(sig.encode()).hexdigest()
        settle = SettleResponse(success=True, transaction=tx, network="eip155:8453", payer=auth["from"])
        self._send(200, resp, {"PAYMENT-RESPONSE": encode_payment_response_header(settle)})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def reset() -> None:
    global quotes_served
    quotes_served = 0
    paid_log.clear()
    user_agents.clear()
    key_log.clear()


def serve(port: int = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    server = serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8402)
    print(f"fake Lookproof API on http://127.0.0.1:{server.server_address[1]}", flush=True)
    server.serve_forever()
