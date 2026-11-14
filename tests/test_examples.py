"""Tests for the examples, against a local fake of the Lookproof API (tests/fake_lookproof.py).

No real money and no network: every payment is signed with a throwaway key and only checked
locally by the fake. Run from the repository root:

    python -m venv .venv && .venv/bin/pip install -r tests/requirements.txt
    .venv/bin/python -m pytest tests
"""
import importlib.util
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-server/src"))
import fake_lookproof  # noqa: E402
from lookproof_mcp import __version__ as MCP_VERSION  # noqa: E402  (only __init__, no dependencies)

ROOT = Path(__file__).resolve().parent.parent
OTHER_PAY_TO = "0x1111111111111111111111111111111111111111"


@pytest.fixture()
def api(monkeypatch):
    for k in ("FAKE_PRICE_FACTOR", "FAKE_PAY_TO", "FAKE_SWITCH_PAY_TO", "FAKE_STATUS", "FAKE_DATA_FILE",
              "X402_PAY", "PRIVATE_KEY", "PRIVATE_KEY_FILE", "MAX_SPEND_USD", "DOMAINS", "DOMAINS_FILE",
              "PAYTO_ALLOWLIST", "STATE_FILE", "ALERT_ON", "DELIVERY", "LOOKPROOF_API_KEY", "FAKE_API_KEY",
              "FAKE_CREDITS"):
        monkeypatch.delenv(k, raising=False)
    fake_lookproof.reset()
    server = fake_lookproof.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("LOOKPROOF_API_URL", url)
    yield url
    server.shutdown()


@pytest.fixture()
def key(monkeypatch):
    k = "0x" + secrets.token_hex(32)
    monkeypatch.setenv("PRIVATE_KEY", k)
    return k


def run(*args, env=None, cwd=None):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, cwd=cwd, timeout=120)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- quickstart ---------------------------------------------------------------

QS = ROOT / "quickstart/python/quickstart.py"


def test_quickstart_dry_run_pays_nothing(api, key):
    r = run(QS, "example.com")
    assert r.returncode == 0, r.stderr
    assert "Price: $0.080 USDC on eip155:8453" in r.stdout
    assert "Dry run: nothing paid" in r.stdout
    assert fake_lookproof.paid_log == []


def test_quickstart_pays_with_flag(api, key):
    r = run(QS, "example.com", "--pay")
    assert r.returncode == 0, r.stderr
    assert "200 domain.health example.com: status ok" in r.stdout
    assert "This run cost $0.080 (tx https://basescan.org/tx/0x" in r.stdout
    assert [p["amount"] for p in fake_lookproof.paid_log] == ["80000"]


def test_quickstart_pays_with_env(api, key):
    r = run(QS, env={"X402_PAY": "1"})
    assert r.returncode == 0, r.stderr
    assert len(fake_lookproof.paid_log) == 1


def test_quickstart_refuses_above_cap(api, key):
    r = run(QS, "--pay", env={"MAX_SPEND_USD": "0.05"})
    assert r.returncode == 1
    assert "exceeds MAX_SPEND_USD" in r.stderr
    assert fake_lookproof.paid_log == []


def test_quickstart_payment_locked_to_quoted_pay_to(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_SWITCH_PAY_TO", OTHER_PAY_TO)
    r = run(QS, "--pay")
    assert r.returncode == 1
    assert "Not paid: the payment terms changed" in r.stderr
    assert fake_lookproof.paid_log == []


def test_quickstart_key_file_must_be_private(api, tmp_path, monkeypatch):
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    f = tmp_path / "wallet.key"
    f.write_text("0x" + secrets.token_hex(32))
    f.chmod(0o644)
    r = run(QS, "--pay", env={"PRIVATE_KEY_FILE": str(f)})
    assert r.returncode == 1 and "chmod 600" in r.stderr
    f.chmod(0o600)
    r = run(QS, "--pay", env={"PRIVATE_KEY_FILE": str(f)})
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(not (ROOT / "quickstart/typescript/node_modules").exists() or not shutil.which("node"),
                    reason="run npm install in quickstart/typescript first")
def test_typescript_quickstart(api, key):
    ts = ROOT / "quickstart/typescript"
    r = subprocess.run(["node", "quickstart.ts"], cwd=ts, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "Dry run: nothing paid" in r.stdout, r.stderr
    assert fake_lookproof.paid_log == []
    r = subprocess.run(["node", "quickstart.ts", "--pay"], cwd=ts, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "This run cost $0.080" in r.stdout, r.stderr
    assert len(fake_lookproof.paid_log) == 1


# --- domain-monitor -----------------------------------------------------------

MON = ROOT / "domain-monitor/monitor.py"


def health_data(**changes) -> dict:
    example = next(e for e in json.loads((ROOT / "docs/endpoints.json").read_text()) if e["id"] == "domain.health")
    data = json.loads(json.dumps(example["example_response"]["data"]))
    for section, fields in changes.items():
        if fields is None:
            data[section] = None
        else:
            data[section].update(fields)
    return data


@pytest.fixture()
def monitor():
    return load_module(MON, "monitor")


def test_posture_and_compare(monitor):
    base = monitor.posture({"data": health_data(), "findings": []})
    assert base["spf"]["label"] == "-all (fail)"
    assert base["dmarc"]["label"] == "p=reject"
    assert base["mta_sts"]["strength"] == 3
    assert monitor.compare("example.com", base, base) == []

    weaker = monitor.posture({"data": health_data(
        spf={"all_qualifier": "~"}, dmarc={"policy": "quarantine", "applied_policy": "quarantine", "pct": 50},
        mta_sts={"policy": {"mode": "testing", "max_age": 86400, "mx": ["*.example.com"], "version": "STSv1"}},
    ), "findings": []})
    kinds = {e["check"]: e["kind"] for e in monitor.compare("example.com", base, weaker)}
    assert kinds == {"spf": "weaker", "dmarc": "weaker", "mta_sts": "weaker"}

    stronger = {e["check"]: e["kind"] for e in monitor.compare("example.com", weaker, base)}
    assert stronger == {"spf": "changed", "dmarc": "changed", "mta_sts": "changed"}


def test_compare_dkim_and_failed_section(monitor):
    base = monitor.posture({"data": health_data(), "findings": []})
    data = health_data(mta_sts=None)
    data["dkim"]["found"][0]["key_bits"] = 1024
    new = monitor.posture({"data": data, "findings": []})
    events = {e["check"]: e for e in monitor.compare("example.com", base, new)}
    assert events["dkim"]["kind"] == "weaker" and "shrank from 2048 to 1024" in events["dkim"]["after"]
    assert events["mta_sts"]["kind"] == "unknown"

    gone = health_data()
    gone["dkim"]["found"] = []
    events = monitor.compare("example.com", base, monitor.posture({"data": gone, "findings": []}))
    assert events[0]["kind"] == "weaker" and "disappeared" in events[0]["after"]


def test_changed_record_with_same_summary_shows_records(monitor):
    base = monitor.posture({"data": health_data(), "findings": []})
    new = monitor.posture({"data": health_data(spf={"record": "v=spf1 include:_spf.example.org -all"}),
                           "findings": []})
    (e,) = monitor.compare("example.com", base, new)
    assert e["kind"] == "changed" and e["after"] == "v=spf1 include:_spf.example.org -all"


def test_spf_permerror_counts_as_weaker(monitor):
    base = monitor.posture({"data": health_data(), "findings": []})
    broken = monitor.posture({"data": health_data(), "findings": [{"code": "SPF_TOO_MANY_LOOKUPS"}]})
    assert monitor.compare("example.com", base, broken)[0]["kind"] == "weaker"


def test_alert_text_is_sanitized(monitor):
    text = monitor.format_events([{"domain": "example.com", "check": "dmarc", "kind": "changed",
                                   "before": "p=reject", "after": "@everyone \x1b[31m `x`" + "a" * 500}])
    assert "\x1b" not in text and "@everyone" not in text and "`" not in text
    assert len(text) < 400


def test_monitor_dry_run_then_paid_runs(api, key, tmp_path, monkeypatch):
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps({"example.com": {"data": health_data()}}))
    env = {"FAKE_DATA_FILE": str(data_file), "STATE_FILE": str(tmp_path / "state.json"), "DOMAINS": "example.com"}
    monkeypatch.setenv("FAKE_DATA_FILE", str(data_file))

    r = run(MON, env=env)
    assert r.returncode == 0 and "Dry run: nothing paid" in r.stdout, r.stderr
    assert fake_lookproof.paid_log == [] and not (tmp_path / "state.json").exists()

    r = run(MON, "--pay", env=env)
    assert r.returncode == 0, r.stderr
    assert "baseline recorded" in r.stdout and "This run cost $0.080" in r.stdout
    assert oct((tmp_path / "state.json").stat().st_mode & 0o777) == "0o600"

    r = run(MON, "--pay", env=env)
    assert "No changes since the previous run" in r.stdout

    data_file.write_text(json.dumps({"example.com": {"data": health_data(dmarc={"policy": "none",
                                                                                  "applied_policy": "none"})}}))
    r = run(MON, "--pay", env=env)
    assert "[WEAKER] example.com DMARC: p=reject -> p=none" in r.stdout
    assert len(fake_lookproof.paid_log) == 3


def test_monitor_refuses_run_over_cap(api, key, tmp_path):
    r = run(MON, "--pay", env={"DOMAINS": "example.com,example.org", "STATE_FILE": str(tmp_path / "s.json")})
    assert r.returncode == 1 and "more than MAX_SPEND_USD" in r.stderr
    assert fake_lookproof.paid_log == []


def test_monitor_rejects_bad_domain(api):
    r = run(MON, "exa mple.com")
    assert r.returncode == 1 and "Not a domain name" in r.stderr


# --- mcp-server ---------------------------------------------------------------

SERVER = ROOT / "mcp-server/src/lookproof_mcp/server.py"
# Run the package from source; tests/test_package.py covers the built and installed wheel.
SERVER_ENV = {"PYTHONPATH": str(ROOT / "mcp-server/src")}


async def mcp_session(env: dict, calls: list[tuple[str, dict]]):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "lookproof_mcp"],
                                   env={**os.environ, **SERVER_ENV, **env})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            results = []
            for name, args in calls:
                res = await session.call_tool(name, args)
                results.append(json.loads(res.content[0].text))
            return tools, results


def mcp_run(env, calls):
    import anyio
    return anyio.run(mcp_session, env, calls)


def test_mcp_tools_show_prices_and_dry_run(api):
    tools, (spending, dry) = mcp_run({}, [("get_spending", {}), ("domain_health", {"domain": "example.com"})])
    paid_tools = [t for t in tools if t.name != "get_spending"]
    assert len(paid_tools) >= 20
    assert all("USDC per call" in t.description for t in paid_tools)
    assert spending["mode"] == "x402" and spending["payments_enabled"] is False
    assert dry["dry_run"] is True and dry["would_cost_usd"] == 0.08
    assert "LOOKPROOF_API_KEY" in dry["note"] and "https://lookproof.dev/pricing" in dry["note"]
    assert fake_lookproof.paid_log == []
    assert fake_lookproof.user_agents == [f"lookproof-mcp/{MCP_VERSION}"]


def test_mcp_pays_and_caps_session(api, key):
    calls = [("domain_health", {"domain": "example.com"}), ("spf_parse", {"record": "v=spf1 -all"}),
             ("dns_lookup", {"name": "example.com", "types": "A,MX"}), ("domain_health", {"domain": "example.org"}),
             ("get_spending", {})]
    _, (health, parse, lookup, capped, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key}, calls)
    assert health["cost_usd"] == 0.08 and health["tx"].startswith("https://basescan.org/tx/0x")
    assert parse["cost_usd"] == 0.002 and lookup["cost_usd"] == 0.005
    assert "Session spending cap reached" in capped["error"]
    assert spending["paid_calls"] == 3 and abs(spending["spent_usd"] - 0.087) < 1e-9
    assert [p["path"] for p in fake_lookproof.paid_log] == ["/v1/domain/health", "/v1/mail/spf-parse", "/v1/dns/lookup"]
    # quote, paid request and 402 retry: every request identifies the client
    assert set(fake_lookproof.user_agents) == {f"lookproof-mcp/{MCP_VERSION}"}


def test_mcp_refuses_price_above_advertised(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_PRICE_FACTOR", "2")
    _, (res,) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "MAX_SPEND_USD": "1"},
                        [("spf", {"domain": "example.com"})])
    assert "more than the advertised" in res["error"]
    assert fake_lookproof.paid_log == []


def test_mcp_payment_locked_to_quote(api, key, monkeypatch):
    monkeypatch.setenv("FAKE_SWITCH_PAY_TO", OTHER_PAY_TO)
    _, (res, spending) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key},
                                 [("spf", {"domain": "example.com"}), ("get_spending", {})])
    assert res["error"].startswith("Not paid: the payment terms changed")
    assert spending["spent_usd"] == 0
    assert fake_lookproof.paid_log == []


# --- mcp-server with an API key ----------------------------------------------

API_KEY = "lp_test_fake"  # the fake API's default valid key


def test_mcp_key_mode_uses_credits_not_wallet(api):
    calls = [("domain_health", {"domain": "example.com"}), ("spf_parse", {"record": "v=spf1 -all"}),
             ("dns_lookup", {"name": "example.com", "types": "A,MX"}), ("get_spending", {})]
    tools, (health, parse, lookup, usage) = mcp_run({"LOOKPROOF_API_KEY": API_KEY}, calls)
    paid_tools = [t for t in tools if t.name != "get_spending"]
    assert len(paid_tools) == 23
    assert all(t.description.endswith("Uses your Lookproof credits.") for t in paid_tools)
    assert not any("USDC" in t.description for t in tools)
    assert health["data"]["endpoint"] == "domain.health" and "cost_usd" not in health and "tx" not in health
    assert health["credits_remaining"] == 249 and health["credits_limit"] == 250
    assert parse["credits_remaining"] == 248 and lookup["credits_remaining"] == 247
    assert usage == {"mode": "api_key", "calls_this_session": 3, "plan": "free",
                     "period_start": "2026-11-01T00:00:00Z", "period_end": "2026-12-01T00:00:00Z",
                     "credits_limit": 250, "credits_used": 3, "credits_remaining": 247, "by_endpoint": []}
    # Sent with the key, never quoted or paid with x402
    assert fake_lookproof.quotes_served == 0 and fake_lookproof.paid_log == []
    assert [k["path"] for k in fake_lookproof.key_log] == ["/v1/domain/health", "/v1/mail/spf-parse", "/v1/dns/lookup"]
    assert set(fake_lookproof.user_agents) == {f"lookproof-mcp/{MCP_VERSION}"}


def test_mcp_key_mode_ignores_wallet_settings(api, key):
    # A wallet key in the environment without X402_PAY is not used: the API key pays.
    _, (res,) = mcp_run({"LOOKPROOF_API_KEY": API_KEY, "PRIVATE_KEY": key}, [("spf", {"domain": "example.com"})])
    assert res["credits_remaining"] == 249
    assert fake_lookproof.paid_log == [] and fake_lookproof.quotes_served == 0


def test_mcp_key_mode_invalid_key(api):
    _, (res, usage) = mcp_run({"LOOKPROOF_API_KEY": "lp_live_revoked"},
                              [("spf", {"domain": "example.com"}), ("get_spending", {})])
    assert res["error"].startswith("HTTP 401, no data.") and "LOOKPROOF_API_KEY" in res["error"]
    assert usage["mode"] == "api_key" and usage["error"].startswith("HTTP 401")
    assert "lp_live_revoked" not in json.dumps([res, usage])  # the key is never echoed back
    assert fake_lookproof.paid_log == [] and fake_lookproof.key_log == []


def test_mcp_key_mode_credits_used_up(api, monkeypatch):
    monkeypatch.setenv("FAKE_CREDITS", "1")
    _, (first, second, usage) = mcp_run({"LOOKPROOF_API_KEY": API_KEY},
                                        [("mx", {"domain": "example.com"}), ("mx", {"domain": "example.org"}),
                                         ("get_spending", {})])
    assert first["credits_remaining"] == 0
    assert second["error"].startswith("HTTP 429") and "lookproof.dev/pricing" in second["error"]
    assert "quota_exceeded" in second["api_error"]
    assert usage["credits_remaining"] == 0 and usage["calls_this_session"] == 1
    assert fake_lookproof.paid_log == []


def test_mcp_key_mode_refuses_bad_settings(api):
    r = run("-m", "lookproof_mcp", env={**SERVER_ENV, "LOOKPROOF_API_KEY": "not-a-lookproof-key"})
    assert r.returncode == 1 and "starts with lp_" in r.stderr
    r = run("-m", "lookproof_mcp", env={**SERVER_ENV, "LOOKPROOF_API_KEY": API_KEY, "X402_PAY": "1"})
    assert r.returncode == 1 and "not both" in r.stderr


def test_mcp_check_matches_endpoint_prices(api):
    r = run("-m", "lookproof_mcp", "--check", env=SERVER_ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 mismatches" in r.stdout


def test_endpoints_doc_has_no_em_dashes():
    for f in ("docs/endpoints.md", "README.md", "quickstart/README.md", "domain-monitor/README.md",
              "mcp-server/README.md"):
        assert "\u2014" not in (ROOT / f).read_text(), f


# --- PAYTO_ALLOWLIST ----------------------------------------------------------

FAKE_PAY_TO = "0x000000000000000000000000000000000000dEaD"


def test_quickstart_payto_allowlist(api, key):
    r = run(QS, "--pay", env={"PAYTO_ALLOWLIST": f"{OTHER_PAY_TO}, {FAKE_PAY_TO.lower()}"})
    assert r.returncode == 0, r.stderr
    r = run(QS, env={"PAYTO_ALLOWLIST": OTHER_PAY_TO})
    assert r.returncode == 1 and "is not in PAYTO_ALLOWLIST" in r.stderr
    r = run(QS, "--pay", env={"PAYTO_ALLOWLIST": "0x123"})
    assert r.returncode == 1 and "not an address" in r.stderr
    assert len(fake_lookproof.paid_log) == 1


@pytest.mark.skipif(not (ROOT / "quickstart/typescript/node_modules").exists() or not shutil.which("node"),
                    reason="run npm install in quickstart/typescript first")
def test_typescript_payto_allowlist(api, key):
    ts = ROOT / "quickstart/typescript"
    r = subprocess.run(["node", "quickstart.ts", "--pay"], cwd=ts, capture_output=True, text=True, timeout=60,
                       env={**os.environ, "PAYTO_ALLOWLIST": OTHER_PAY_TO})
    assert r.returncode == 1 and "is not in PAYTO_ALLOWLIST" in r.stderr
    assert fake_lookproof.paid_log == []


def test_monitor_payto_allowlist(api, key, tmp_path):
    env = {"DOMAINS": "example.com", "STATE_FILE": str(tmp_path / "s.json"), "PAYTO_ALLOWLIST": OTHER_PAY_TO}
    r = run(MON, "--pay", env=env)
    assert r.returncode == 1 and "is not in PAYTO_ALLOWLIST" in r.stderr
    assert fake_lookproof.paid_log == []


def test_mcp_payto_allowlist(api, key):
    _, (res,) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "PAYTO_ALLOWLIST": OTHER_PAY_TO},
                        [("spf", {"domain": "example.com"})])
    assert "not in PAYTO_ALLOWLIST" in res["error"]
    _, (res,) = mcp_run({"X402_PAY": "1", "PRIVATE_KEY": key, "PAYTO_ALLOWLIST": FAKE_PAY_TO},
                        [("spf", {"domain": "example.com"})])
    assert res["cost_usd"] == 0.01
    assert len(fake_lookproof.paid_log) == 1


def test_mcp_readme_accounts_for_every_endpoint():
    import re
    paths = {e["path"] for e in json.loads((ROOT / "docs/endpoints.json").read_text())}
    tools = set(re.findall(r'await call\("(?:GET|POST)", "([^"]+)"', SERVER.read_text()))
    section = (ROOT / "mcp-server/README.md").read_text().split("## Endpoints without a tool")[1].split("\n## ")[0]
    omitted = set(re.findall(r"(/v1/[a-z0-9/-]+)", section))
    assert tools | omitted == paths and not tools & omitted
