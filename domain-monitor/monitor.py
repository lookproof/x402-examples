"""Domain monitor: check a list of domains with Lookproof's domain health check (x402, USDC on Base)
and alert when SPF, DKIM, DMARC or MTA-STS changes or gets weaker.

Dry run by default: shows the domains, the price per check and the cost per run, then stops.
Pass --pay (or X402_PAY=1) to check. Made for cron: one run checks every domain once, keeps the
latest result per domain in a state file and alerts only on a difference from the previous run.

Usage:
    python monitor.py [domain ...] [--pay] [--test-alert]

Domains come from the arguments, else DOMAINS (comma-separated), else DOMAINS_FILE (one per line).
Responses from the API are data: they are compared and quoted in alerts, never followed.
"""
import asyncio
import hashlib
import json
import os
import re
import smtplib
import ssl
import sys
import tempfile
import time
from email.message import EmailMessage
from pathlib import Path

import httpx
from eth_account import Account
from x402 import x402Client
from x402.http import decode_payment_required_header, decode_payment_response_header
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact.register import register_exact_evm_client
from x402.schemas.errors import NoMatchingRequirementsError

HERE = Path(__file__).resolve().parent
API = os.getenv("LOOKPROOF_API_URL", "https://api.lookproof.dev").rstrip("/")
PATH = "/v1/domain/health"
EXPECTED_PRICE = 0.08  # documented price of /v1/domain/health; a higher quote is refused
MAX_SPEND = float(os.getenv("MAX_SPEND_USD") or "0.10")
PAY = "--pay" in sys.argv or os.getenv("X402_PAY") == "1"
STATE_FILE = Path(os.path.expanduser(os.getenv("STATE_FILE") or HERE / ".monitor-state.json"))
ALERT_ON = (os.getenv("ALERT_ON") or "change").strip().lower()  # change | weaker
DELIVERY = [d.strip().lower() for d in (os.getenv("DELIVERY") or "stdout").split(",") if d.strip()]
MAX_DOMAINS = 50
PAUSE_S = 1.0  # stay well inside the API's 60 requests/minute per IP

BASE_MAINNET = "eip155:8453"
USDC_ON_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$")


def stop(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


# --- Input ------------------------------------------------------------------

def load_domains(argv: list[str]) -> list[str]:
    raw = [a for a in argv if not a.startswith("--")]
    if not raw and os.getenv("DOMAINS"):
        raw = os.environ["DOMAINS"].split(",")
    if not raw and os.getenv("DOMAINS_FILE"):
        lines = Path(os.path.expanduser(os.environ["DOMAINS_FILE"])).read_text().splitlines()
        raw = [ln.split("#", 1)[0] for ln in lines]
    domains = []
    for d in (x.strip().lower().rstrip(".") for x in raw):
        if not d:
            continue
        if not DOMAIN_RE.match(d):
            stop(f"Not a domain name: {d!r}")
        if d not in domains:
            domains.append(d)
    if not domains:
        stop("No domains. Pass them as arguments, or set DOMAINS or DOMAINS_FILE.")
    if len(domains) > MAX_DOMAINS:
        stop(f"{len(domains)} domains; this example checks at most {MAX_DOMAINS} per run.")
    return domains


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


# --- Posture: the parts of a result that are compared between runs ----------

SPF_ALL = {"-": (3, "-all (fail)"), "~": (2, "~all (softfail)"), "?": (1, "?all (neutral)"),
           "+": (0, "+all (anyone may send)")}
SPF_BROKEN = {"SPF_TOO_MANY_LOOKUPS", "SPF_SYNTAX_ERROR", "SPF_MULTIPLE_RECORDS", "SPF_INCLUDE_LOOP"}
DMARC_RANK = {"none": 1, "quarantine": 2, "reject": 3}
STS_RANK = {"none": 1, "testing": 2, "enforce": 3}


def digest(text: str | None) -> str | None:
    return hashlib.sha256(text.encode()).hexdigest()[:16] if text else None


def spf_posture(spf: dict, codes: set[str]) -> dict:
    record = spf.get("record")
    if not record:
        return {"strength": 0, "label": "no SPF record", "record": None}
    strength, label = SPF_ALL.get(spf.get("all_qualifier"), (1, "no all mechanism"))
    broken = sorted(codes & SPF_BROKEN)
    if broken:
        strength, label = 0, f"{label}, but invalid ({', '.join(broken)})"
    return {"strength": strength, "label": label, "record": record}


def dmarc_posture(dmarc: dict) -> dict:
    if not dmarc.get("record"):
        return {"strength": [0, 0, 0], "label": "no DMARC record", "record": None}
    policy = dmarc.get("applied_policy") or dmarc.get("policy")
    pct = dmarc.get("pct") if dmarc.get("pct") is not None else 100
    test = bool(dmarc.get("test_mode"))
    label = f"p={policy}" + (f" pct={pct}" if pct != 100 else "") + (" (test mode)" if test else "")
    # Compared in order: policy, then pct, then not-in-test-mode.
    return {"strength": [DMARC_RANK.get(policy, 0), pct, 0 if test else 1], "label": label,
            "record": dmarc.get("record"), "subdomain_policy": dmarc.get("subdomain_policy")}


def dkim_posture(dkim: dict) -> dict:
    keys = {}
    for k in dkim.get("found", []):
        keys[k.get("selector")] = {"bits": k.get("key_bits"), "type": k.get("key_type"),
                                   "revoked": bool(k.get("revoked")), "testing": bool(k.get("testing")),
                                   "key": digest(k.get("record"))}
    if not keys:
        label = "no DKIM key found on the common selectors"
    else:
        label = ", ".join(f"{s} ({v['type']} {v['bits']} bit{', revoked' if v['revoked'] else ''})"
                          for s, v in sorted(keys.items()))
    return {"label": label, "selectors": keys}


def mta_sts_posture(sts: dict) -> dict:
    if not sts.get("record"):
        return {"strength": 0, "label": "no MTA-STS record"}
    policy = sts.get("policy") or {}
    if not sts.get("policy_fetched"):
        return {"strength": 0, "label": "MTA-STS record, but the policy could not be fetched",
                "policy_id": sts.get("policy_id")}
    mode = policy.get("mode")
    uncovered = sorted(sts.get("uncovered_mx") or [])
    label = f"mode={mode} max_age={policy.get('max_age')}" + (f", MX not covered: {', '.join(uncovered)}"
                                                              if uncovered else "")
    return {"strength": STS_RANK.get(mode, 0), "label": label, "policy_id": sts.get("policy_id"),
            "mx": sorted(policy.get("mx") or []), "uncovered_mx": uncovered}


def posture(result: dict) -> dict:
    """Extract the compared fields. A section that failed is None (unknown, not 'missing')."""
    data = result.get("data") or {}
    codes = {f.get("code") for f in result.get("findings", []) if isinstance(f, dict)}
    out = {}
    for name, fn in (("spf", lambda s: spf_posture(s, codes)), ("dkim", dkim_posture),
                     ("dmarc", dmarc_posture), ("mta_sts", mta_sts_posture)):
        section = data.get(name)
        out[name] = fn(section) if isinstance(section, dict) else None
    return out


def weaker_dkim(old: dict, new: dict) -> list[str]:
    why = []
    for sel, o in old["selectors"].items():
        n = new["selectors"].get(sel)
        if n is None:
            why.append(f"selector {sel} disappeared")
        elif n["revoked"] and not o["revoked"]:
            why.append(f"selector {sel} was revoked")
        elif (n["bits"] or 0) < (o["bits"] or 0):
            why.append(f"selector {sel} key shrank from {o['bits']} to {n['bits']} bit")
        elif n["testing"] and not o["testing"]:
            why.append(f"selector {sel} switched to testing mode")
    return why


def compare(domain: str, old: dict | None, new: dict) -> list[dict]:
    """Events between two postures: weaker, changed or unknown (check failed this run)."""
    events = []
    for check in ("spf", "dkim", "dmarc", "mta_sts"):
        o, n = (old or {}).get(check), new.get(check)
        if n is None:
            events.append({"domain": domain, "check": check, "kind": "unknown",
                           "before": o["label"] if o else None, "after": "check failed this run"})
            continue
        if o is None or o == n:
            continue
        if check == "dkim":
            reasons = weaker_dkim(o, n)
            kind = "weaker" if reasons else "changed"
        else:
            reasons = []
            kind = "weaker" if n["strength"] < o["strength"] else "changed"
            if check == "mta_sts" and len(n.get("uncovered_mx", [])) > len(o.get("uncovered_mx", [])):
                kind = "weaker"
        before, after = o["label"], n["label"]
        if before == after:  # same summary: show what differs underneath
            before, after = detail(check, o), detail(check, n)
        events.append({"domain": domain, "check": check, "kind": kind, "before": before,
                       "after": after + (f" ({'; '.join(reasons)})" if reasons else "")})
    return events


def detail(check: str, p: dict) -> str:
    if check in ("spf", "dmarc"):
        return p.get("record") or p["label"]
    if check == "dkim":
        return ", ".join(f"{s} key {v['key']}" for s, v in sorted(p["selectors"].items())) or p["label"]
    return f"{p['label']}, policy id {p.get('policy_id')}, mx {', '.join(p.get('mx') or []) or '-'}"


# --- State ------------------------------------------------------------------

def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except FileNotFoundError:
        return {"domains": {}}


def save_state(state: dict) -> None:
    """Write atomically (temp file + rename), readable only by you."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_FILE.parent, prefix=".monitor-state.")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.chmod(tmp, 0o600)
    os.replace(tmp, STATE_FILE)


# --- Alerts -----------------------------------------------------------------

CHECK_NAMES = {"spf": "SPF", "dkim": "DKIM", "dmarc": "DMARC", "mta_sts": "MTA-STS"}


def clean(text, limit: int = 160) -> str:
    """Quote API data safely: printable characters only, no mentions, bounded length."""
    s = "".join(c if c.isprintable() else " " for c in str(text))
    s = s.replace("@", "@​").replace("`", "'")
    return s if len(s) <= limit else s[: limit - 3] + "..."


def format_events(events: list[dict]) -> str:
    lines = []
    for e in events:
        tag = {"weaker": "WEAKER", "changed": "CHANGED", "unknown": "UNKNOWN"}[e["kind"]]
        lines.append(f"[{tag}] {e['domain']} {CHECK_NAMES[e['check']]}: "
                     f"{clean(e['before'])} -> {clean(e['after'])}")
    return "\n".join(lines)


def send_discord(subject: str, text: str) -> None:
    url = os.environ["DISCORD_WEBHOOK_URL"]
    body = {"content": f"{subject}\n{text}"[:1990], "allowed_mentions": {"parse": []}}
    r = httpx.post(url, json=body, timeout=30)
    if r.is_error:  # never print the URL: it is the webhook secret
        raise RuntimeError(f"Discord answered HTTP {r.status_code}")


def send_telegram(subject: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    try:
        r = httpx.post(url, json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": f"{subject}\n{text}"[:4000],
                                  "disable_web_page_preview": True}, timeout=30)
    except httpx.HTTPError as e:  # the URL contains the bot token: report the type only
        raise RuntimeError(f"Telegram request failed: {type(e).__name__}") from None
    if r.is_error:
        raise RuntimeError(f"Telegram answered HTTP {r.status_code}")


def send_email(subject: str, text: str) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ["MAIL_FROM"], os.environ["MAIL_TO"]
    msg.set_content(text + "\n")
    host, port = os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT") or "587")
    ctx = ssl.create_default_context()
    smtp = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) if port == 465 else smtplib.SMTP(host, port, timeout=30)
    with smtp:
        if port != 465:
            smtp.starttls(context=ctx)
        if os.getenv("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)


SENDERS = {"discord": send_discord, "telegram": send_telegram, "email": send_email}


def deliver(subject: str, text: str) -> bool:
    ok = True
    for channel in DELIVERY:
        if channel == "stdout":
            print(f"{subject}\n{text}")
            continue
        try:
            SENDERS[channel](subject, text)
        except KeyError as e:
            ok = False
            print(f"Alert via {channel} not sent: missing setting {e}", file=sys.stderr)
        except Exception as e:
            ok = False
            print(f"Alert via {channel} not sent: {clean(e)}", file=sys.stderr)
    return ok


# --- Paying ---------------------------------------------------------------

async def quote(http: httpx.AsyncClient, domain: str):
    r = await http.get(API + PATH, params={"domain": domain})
    if r.status_code != 402 or "PAYMENT-REQUIRED" not in r.headers:
        raise RuntimeError(f"expected 402, got HTTP {r.status_code}")
    for req in decode_payment_required_header(r.headers["PAYMENT-REQUIRED"]).accepts:
        if req.scheme == "exact" and req.network == BASE_MAINNET and req.asset.lower() == USDC_ON_BASE:
            return req
    raise RuntimeError("the 402 offers no USDC payment on Base mainnet")


async def pay_and_check(domain: str, q, signer) -> tuple[dict, str | None]:
    """Pay exactly the quote (amount, asset, network, payTo locked) and return the result and tx hash."""
    client = x402Client().set_spend_controls({"max_amount_per_payment": f"${int(q.amount) / 1e6:.6f}"})
    client.register_policy(lambda version, reqs: [
        r for r in reqs if r.amount == q.amount and r.network == q.network
        and r.asset.lower() == q.asset.lower() and r.pay_to.lower() == q.pay_to.lower()])
    register_exact_evm_client(client, signer)
    async with x402HttpxClient(client, timeout=60) as http:
        r = await http.get(API + PATH, params={"domain": domain})
    receipt = r.headers.get("PAYMENT-RESPONSE")
    tx = decode_payment_response_header(receipt).transaction if receipt else None
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}" + (f" (settled, tx {tx})" if tx else ""))
    return r.json(), tx


async def run(domains: list[str]) -> int:
    async with httpx.AsyncClient(timeout=30) as http:
        first = await quote(http, domains[0])
    price = int(first.amount) / 1e6
    total = price * len(domains)
    print(f"{len(domains)} domains x ${price:.3f} = ${total:.3f} per run "
          f"(${total * 30:.2f} per 30 days if run daily). USDC on {first.network}, payTo {first.pay_to}")
    allow = payto_allowlist()
    if allow and first.pay_to.lower() not in allow:
        stop(f"payTo {first.pay_to} is not in PAYTO_ALLOWLIST. Not paying.")
    if not PAY:
        print("Dry run: nothing paid. Re-run with --pay (or X402_PAY=1) to check the domains.")
        return 0
    if price > EXPECTED_PRICE + 1e-9:
        stop(f"Quoted ${price:.3f}, more than the documented ${EXPECTED_PRICE:.3f}. Not paying.")
    if total > MAX_SPEND + 1e-9:
        stop(f"This run would cost ${total:.3f}, more than MAX_SPEND_USD={MAX_SPEND:g}. "
             f"Raise MAX_SPEND_USD to at least {total:.2f} or check fewer domains.")

    signer = EthAccountSigner(Account.from_key(load_private_key()))
    state = load_state()
    events, failures, spent, txs, compared = [], [], 0.0, [], 0
    for i, domain in enumerate(domains):
        if i:
            time.sleep(PAUSE_S)
        try:
            async with httpx.AsyncClient(timeout=30) as http:
                q = await quote(http, domain)
        except Exception as e:
            failures.append(f"{domain}: not checked, {clean(e)}")
            continue
        p = int(q.amount) / 1e6
        if allow and q.pay_to.lower() not in allow:
            failures.append(f"{domain}: not checked, payTo {q.pay_to} is not in PAYTO_ALLOWLIST")
            continue
        if p > EXPECTED_PRICE + 1e-9 or spent + p > MAX_SPEND + 1e-9:
            failures.append(f"{domain}: not checked, would exceed the price or MAX_SPEND_USD")
            continue
        spent += p  # counted before paying: a failure after signing may still have been paid
        try:
            result, tx = await pay_and_check(domain, q, signer)
        except Exception as e:
            if isinstance(e, NoMatchingRequirementsError) or isinstance(e.__cause__, NoMatchingRequirementsError):
                spent -= p  # refused before anything was signed
                failures.append(f"{domain}: not paid, payment terms changed since the quote")
            else:
                failures.append(f"{domain}: possibly paid ${p:.3f}, no result ({clean(e)})")
            continue
        if tx:
            txs.append(tx)
        new = posture(result)
        prev = state["domains"].get(domain)
        if prev is None:
            print(f"{domain}: baseline recorded")
            for check, v in new.items():
                print(f"  {CHECK_NAMES[check]:<8} {clean(v['label']) if v else 'check failed'}")
        compared += prev is not None
        domain_events = compare(domain, prev and prev["posture"], new)
        events += domain_events
        # Keep the last known value of a section that failed this run.
        merged = {k: (v if v is not None else (prev or {}).get("posture", {}).get(k)) for k, v in new.items()}
        state["domains"][domain] = {"posture": merged, "checked_at": result.get("checked_at"),
                                    "status": result.get("status"), "request_id": result.get("request_id")}
    state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_state(state)

    alert = [e for e in events if e["kind"] in ("weaker", "unknown")] if ALERT_ON == "weaker" else events
    ok = True
    if alert:
        n = {k: sum(e["kind"] == k for e in alert) for k in ("weaker", "changed", "unknown")}
        subject = f"Lookproof monitor: {n['weaker']} weaker, {n['changed']} changed, {n['unknown']} not checked"
        ok = deliver(subject, format_events(alert))
    elif compared:
        print(f"No changes since the previous run ({compared} domain(s) compared).")
    for f in failures:
        print(f, file=sys.stderr)
    print(f"This run cost ${spent:.3f} ({len(txs)} payments" + (f", last tx https://basescan.org/tx/{txs[-1]})"
                                                                 if txs else ")"))
    return 0 if ok and not failures else 1


def main() -> None:
    if "--test-alert" in sys.argv:  # free: no API call, just the delivery channels
        sys.exit(0 if deliver("Lookproof monitor: test alert",
                              "[WEAKER] example.com DMARC: p=reject -> p=none (test message)") else 1)
    sys.exit(asyncio.run(run(load_domains(sys.argv[1:]))))


if __name__ == "__main__":
    main()
