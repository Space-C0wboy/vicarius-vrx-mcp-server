import pytest
from fastmcp import FastMCP

from vrx_mcp.tools import request as request_tool


async def _tool_names(mcp):
    # FastMCP 3.x: list_tools() returns a Sequence[Tool] (each with .name),
    # not the dict that get_tools() returned in 2.x.
    tools = await mcp.list_tools()
    return {tool.name for tool in tools}


async def test_registers_vrx_request():
    mcp = FastMCP(name="t")
    request_tool.register(mcp, read_only=False)
    assert "vrx_request" in await _tool_names(mcp)


async def test_read_only_rejects_non_get(monkeypatch):
    captured = {}

    class FakeClient:
        async def request(self, method, path, *, params=None, json=None):
            captured["method"] = method
            return {"ok": True}

    async def fake_get_client():
        return FakeClient()

    monkeypatch.setattr(request_tool, "get_client", fake_get_client)

    # GET is allowed in read-only
    assert await request_tool._do_request("GET", "/x", None, None, read_only=True) == {"ok": True}
    # POST is rejected in read-only
    with pytest.raises(ValueError):
        await request_tool._do_request("POST", "/x", None, None, read_only=True)
