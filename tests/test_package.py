"""Tests for the lookproof-mcp package: build it with uv, install the wheel in an empty venv and run
the installed `lookproof-mcp` command against the local fake API (tests/fake_lookproof.py).

Needs uv (https://docs.astral.sh/uv/) and network access to PyPI for the package's dependencies.
Skipped without uv, except in CI, where a missing uv is a failure. Set PACKAGE_TEST_PYTHON (e.g. 3.10)
to install into a venv with another Python than the one running pytest.

    .venv/bin/python -m pytest tests/test_package.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import tomllib
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fake_lookproof  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "mcp-server"
SERVER_NAME = "io.github.lookproof/lookproof-mcp"
VERSION = re.search(r'__version__ = "([^"]+)"', (PKG / "src/lookproof_mcp/__init__.py").read_text())[1]

if not shutil.which("uv"):
    if os.getenv("CI"):
        pytest.fail("uv is required for the package tests in CI", pytrace=False)
    pytest.skip("uv is not installed", allow_module_level=True)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Build sdist and wheel, then install the wheel into an empty venv (no pip, nothing else in it)."""
    tmp = tmp_path_factory.mktemp("pkg")
    dist = tmp / "dist"
    subprocess.run(["uv", "build", "--out-dir", str(dist), str(PKG)], check=True, capture_output=True, text=True)
    (wheel,) = dist.glob("lookproof_mcp-*.whl")
    (sdist,) = dist.glob("lookproof_mcp-*.tar.gz")
    venv = tmp / "venv"
    # PACKAGE_TEST_PYTHON picks the interpreter for the venv (e.g. 3.10), so CI can test the oldest
    # supported Python while pytest itself runs on a newer one.
    subprocess.run(["uv", "venv", "--quiet", "--python", os.getenv("PACKAGE_TEST_PYTHON") or sys.executable,
                    str(venv)], check=True)
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(["uv", "pip", "install", "--python", str(py), str(wheel)], check=True, capture_output=True,
                   text=True)
    exe = venv / ("Scripts/lookproof-mcp.exe" if os.name == "nt" else "bin/lookproof-mcp")
    assert exe.exists()
    return {"wheel": wheel, "sdist": sdist, "exe": exe}


@pytest.fixture()
def api(monkeypatch):
    for k in ("FAKE_PRICE_FACTOR", "FAKE_PAY_TO", "FAKE_SWITCH_PAY_TO", "FAKE_STATUS", "FAKE_DATA_FILE",
              "X402_PAY", "PRIVATE_KEY", "PRIVATE_KEY_FILE", "MAX_SPEND_USD", "PAYTO_ALLOWLIST", "PYTHONPATH"):
        monkeypatch.delenv(k, raising=False)
    fake_lookproof.reset()
    server = fake_lookproof.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("LOOKPROOF_API_URL", url)
    yield url
    server.shutdown()


def run(exe, *args, env=None):
    # Run from an empty directory, so nothing from the repository can be imported by accident.
    return subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=120,
                          env={**os.environ, **(env or {})}, cwd=exe.parent)


def test_version(built):
    r = run(built["exe"], "--version")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == f"lookproof-mcp {VERSION}"


def test_help(built):
    r = run(built["exe"], "--help")
    assert r.returncode == 0 and "--check" in r.stdout and "X402_PAY" in r.stdout


def test_installed_dry_run_pays_nothing(built, api):
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def session():
        params = StdioServerParameters(command=str(built["exe"]), env=dict(os.environ), cwd=str(built["exe"].parent))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as s:
                init = await s.initialize()
                tools = (await s.list_tools()).tools
                res = await s.call_tool("domain_health", {"domain": "example.com"})
                return init, tools, json.loads(res.content[0].text)

    init, tools, dry = anyio.run(session)
    assert init.server_info.name == "lookproof" and init.server_info.version == VERSION
    assert len(tools) == 24
    assert dry["dry_run"] is True and dry["would_cost_usd"] == 0.08
    assert fake_lookproof.paid_log == []
    assert fake_lookproof.user_agents == [f"lookproof-mcp/{VERSION}"]


def test_installed_check(built, api, monkeypatch):
    r = run(built["exe"], "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "23 paid tools, 0 mismatches" in r.stdout
    assert fake_lookproof.paid_log == []
    monkeypatch.setenv("FAKE_PRICE_FACTOR", "2")  # read by the fake API in this process
    r = run(built["exe"], "--check")
    assert r.returncode == 1 and "23 mismatches" in r.stdout


def test_pay_without_key_refuses_to_start(built, api):
    r = run(built["exe"], env={"X402_PAY": "1"})
    assert r.returncode == 1 and "needs PRIVATE_KEY or PRIVATE_KEY_FILE" in r.stderr


def test_wheel_contents_and_metadata(built):
    with zipfile.ZipFile(built["wheel"]) as z:
        names = z.namelist()
        meta = z.read(f"lookproof_mcp-{VERSION}.dist-info/METADATA").decode()
        entry = z.read(f"lookproof_mcp-{VERSION}.dist-info/entry_points.txt").decode()
    assert {n for n in names if not n.startswith(f"lookproof_mcp-{VERSION}.dist-info/")} == {
        "lookproof_mcp/__init__.py", "lookproof_mcp/__main__.py", "lookproof_mcp/server.py"}
    assert "Name: lookproof-mcp" in meta and f"Version: {VERSION}" in meta
    assert "Requires-Python: >=3.10" in meta and "License-Expression: MIT" in meta
    assert "Project-URL: Homepage, https://lookproof.dev" in meta
    assert "Project-URL: Source, https://github.com/lookproof/x402-examples" in meta
    # The MCP registry checks this string in the PyPI description, which is the README.
    assert f"mcp-name: {SERVER_NAME}" in meta
    assert "lookproof-mcp = lookproof_mcp.server:main" in entry


def test_sdist_contents(built):
    with tarfile.open(built["sdist"]) as t:
        names = {n.split("/", 1)[1] for n in t.getnames() if "/" in n}
    assert {"README.md", "LICENSE", "CHANGELOG.md", "pyproject.toml", "src/lookproof_mcp/server.py"} <= names
    assert not any(n.endswith((".key", ".env")) or "server.json" in n for n in names)


def test_server_json_matches_package():
    sj = json.loads((PKG / "server.json").read_text())
    pyproject = tomllib.loads((PKG / "pyproject.toml").read_text())
    assert sj["$schema"].startswith("https://static.modelcontextprotocol.io/schemas/")
    assert sj["name"] == SERVER_NAME
    assert 1 <= len(sj["description"]) <= 100  # registry schema limit
    assert sj["version"] == VERSION
    assert sj["repository"] == {"url": "https://github.com/lookproof/x402-examples", "source": "github",
                                "subfolder": "mcp-server"}
    (pkg,) = sj["packages"]
    assert pkg["registryType"] == "pypi" and pkg["registryBaseUrl"] == "https://pypi.org"
    assert pkg["identifier"] == pyproject["project"]["name"] == "lookproof-mcp"
    assert pkg["version"] == VERSION and pkg["transport"] == {"type": "stdio"}
    env_names = {e["name"] for e in pkg["environmentVariables"]}
    assert env_names == {"X402_PAY", "PRIVATE_KEY_FILE", "PRIVATE_KEY", "MAX_SPEND_USD", "PAYTO_ALLOWLIST"}
    assert all(e.get("isSecret") for e in pkg["environmentVariables"] if e["name"] == "PRIVATE_KEY")
    assert f"## {VERSION} " in (PKG / "CHANGELOG.md").read_text()
    # The hosted server (lookproof/lookproof, api.lookproof.dev/mcp): an API key, no wallet.
    (remote,) = sj["remotes"]
    assert remote["type"] == "streamable-http" and remote["url"] == "https://api.lookproof.dev/mcp"
    (header,) = remote["headers"]
    assert header["name"] == "Authorization" and header["isSecret"] and header["isRequired"]


def test_package_docs_have_no_em_dashes_or_relative_links():
    readme = (PKG / "README.md").read_text()
    assert re.search(rf"^<!-- mcp-name: {re.escape(SERVER_NAME)} -->$", readme, re.M)
    assert "uvx lookproof-mcp" in readme
    # PyPI renders the README without the repository, so links must be absolute.
    assert not re.search(r"\]\((?!https://|#)", readme)
    for f in ("README.md", "CHANGELOG.md", "server.json", "pyproject.toml"):
        assert "\u2014" not in (PKG / f).read_text(), f
