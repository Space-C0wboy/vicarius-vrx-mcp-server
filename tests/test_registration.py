import pytest
from fastmcp import FastMCP

from vrx_mcp import config as config_mod


@pytest.fixture(autouse=True)
def _reset():
    config_mod.reset_config_cache()
    yield
    config_mod.reset_config_cache()


async def _names(mcp):
    # FastMCP 3.x: list_tools() returns tool objects with a .name attribute.
    tools = await mcp.list_tools()
    return {t.name for t in tools}


async def test_full_mode_registers_mutating_and_escape_hatch(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", "https://x.vicarius.cloud/vicarius-external-data-api")
    monkeypatch.setenv("VRX_READ_ONLY", "false")
    config_mod.reset_config_cache()
    from vrx_mcp.tools import register_all
    mcp = FastMCP(name="t")
    register_all(mcp)
    names = await _names(mcp)
    assert "vrx_request" in names
    # at least one known mutating tool present
    assert "endpoint_delete" in names


async def test_read_only_hides_mutating(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", "https://x.vicarius.cloud/vicarius-external-data-api")
    monkeypatch.setenv("VRX_READ_ONLY", "true")
    config_mod.reset_config_cache()
    from vrx_mcp.tools import register_all
    mcp = FastMCP(name="t")
    register_all(mcp)
    names = await _names(mcp)
    assert "vrx_request" in names
    assert "endpoint_delete" not in names
    # a non-mutating search tool is still present
    assert "endpoint_search" in names
