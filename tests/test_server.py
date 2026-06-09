import pytest

from vrx_mcp import config as config_mod


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.delenv("VRX_API_KEY", raising=False)
    monkeypatch.delenv("VRX_BASE_URL", raising=False)
    config_mod.reset_config_cache()
    yield
    config_mod.reset_config_cache()


def test_build_server_ok(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", "https://x.vicarius.cloud/vicarius-external-data-api")
    config_mod.reset_config_cache()
    from fastmcp import FastMCP

    from vrx_mcp.server import build_server
    mcp = build_server()
    assert isinstance(mcp, FastMCP)


def test_main_exits_2_on_config_error(monkeypatch):
    monkeypatch.delenv("VRX_API_KEY", raising=False)
    config_mod.reset_config_cache()
    from vrx_mcp.server import main
    rc = main(["--transport", "stdio"])
    assert rc == 2
