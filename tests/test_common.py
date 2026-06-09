import pytest

from vrx_mcp.tools import _common


def test_drop_none():
    assert _common.drop_none({"a": 1, "b": None, "c": 0}) == {"a": 1, "c": 0}


def test_coerce_json_parses_object_string():
    assert _common.coerce_json('{"a": 1}') == {"a": 1}


def test_coerce_json_parses_array_string():
    assert _common.coerce_json('[1, 2]') == [1, 2]


def test_coerce_json_leaves_plain_string():
    assert _common.coerce_json("endpointId==5") == "endpointId==5"


def test_coerce_json_leaves_non_string():
    assert _common.coerce_json(5) == 5


async def test_execute_request_interpolates_path_and_cleans(monkeypatch):
    captured = {}

    class FakeClient:
        async def request(self, method, path, *, params=None, json=None):
            captured.update(method=method, path=path, params=params, json=json)
            return {"ok": True}

    async def fake_get_client():
        return FakeClient()

    monkeypatch.setattr(_common, "get_client", fake_get_client)

    out = await _common.execute_request(
        "GET", "/endpoint/{id}/detail",
        path_params={"id": 42},
        query={"from": 0, "size": None, "q": '{"x":1}'},
        body=None,
    )
    assert out == {"ok": True}
    assert captured["path"] == "/endpoint/42/detail"
    assert captured["params"] == {"from": 0, "q": {"x": 1}}  # None dropped, json-coerced
    assert captured["json"] is None
