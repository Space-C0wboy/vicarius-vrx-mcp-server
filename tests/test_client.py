import os

import httpx
import pytest

from vrx_mcp.client import VrxClient, _parse_retry_after
from vrx_mcp.config import Config
from vrx_mcp.errors import VrxAPIError


def _config(**over):
    base = dict(
        api_key=os.environ.get("VRX_API_KEY", "dummy"), base_url="https://x.vicarius.cloud/vicarius-external-data-api",
        auth_header="vicarius-token", read_only=False, timeout=5.0,
        log_level="INFO", http_host="127.0.0.1", http_port=8765,
    )
    base.update(over)
    return Config(**base)


def _client(handler, **over):
    return VrxClient(config=_config(**over), transport=httpx.MockTransport(handler))


async def test_get_returns_json_and_sends_auth_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("vicarius-token")
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    async with _client(handler) as c:
        data = await c.request("GET", "/endpoint/search", params={"from": 0, "size": 10})
    assert data == {"ok": True}
    assert seen["auth"] == os.environ.get("VRX_API_KEY", "dummy")
    assert "from=0" in seen["url"] and "size=10" in seen["url"]


async def test_custom_auth_header_name():
    seen = {}

    def handler(request):
        seen["hdr"] = request.headers.get("authorization")
        return httpx.Response(200, json={})

    async with _client(handler, auth_header="authorization") as c:
        await c.request("GET", "/x")
    assert seen["hdr"] == os.environ.get("VRX_API_KEY", "dummy")


async def test_http_error_raises():
    def handler(request):
        return httpx.Response(403, json={"message": "forbidden"})

    async with _client(handler) as c:
        with pytest.raises(VrxAPIError) as ei:
            await c.request("GET", "/x")
    assert ei.value.status_code == 403
    assert "forbidden" in str(ei.value)


async def test_retries_then_succeeds_on_429():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"X-Rate-Limit-Retry-After-Seconds": "0"})
        return httpx.Response(200, json={"ok": 1})

    async with _client(handler) as c:
        data = await c.request("GET", "/x")
    assert data == {"ok": 1}
    assert calls["n"] == 2


async def test_post_sends_json_body():
    seen = {}

    def handler(request):
        seen["body"] = request.content
        seen["method"] = request.method
        return httpx.Response(200, json={})

    async with _client(handler) as c:
        await c.request("POST", "/vulnerability/search", json={"q": "a==b"})
    assert seen["method"] == "POST"
    assert b"a==b" in seen["body"]


def test_parse_retry_after_prefers_ratelimit_header():
    headers = httpx.Headers({"X-Rate-Limit-Retry-After-Seconds": "12", "Retry-After": "99"})
    assert _parse_retry_after(headers) == 12.0


def test_parse_retry_after_falls_back_to_standard():
    assert _parse_retry_after(httpx.Headers({"Retry-After": "7"})) == 7.0


def test_parse_retry_after_none_when_absent():
    assert _parse_retry_after(httpx.Headers({})) is None
