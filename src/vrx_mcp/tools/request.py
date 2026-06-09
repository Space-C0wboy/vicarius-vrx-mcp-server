"""Generic escape-hatch tool: issue an arbitrary request against the vRx API."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..client import get_client
from ._common import coerce_json, drop_none

_DESCRIPTION = (
    "Issue an arbitrary request to the Vicarius vRx External Data API for endpoints "
    "without a dedicated tool. `path` is relative to the API base "
    "(e.g. '/endpoint/search'). Search uses RSQL in the `q` query param: == (equals), "
    "=in=(a,b) (in-list), =re='regex' (regex), > / < (compare). Pagination: `size` <= 500, "
    "`from` (offset) <= 10000; beyond 10000 use seek paging (sort + a q comparison on the "
    "last value). In read-only mode only GET is permitted."
)


async def _do_request(
    method: str,
    path: str,
    query: Any | None,
    body: Any | None,
    *,
    read_only: bool,
) -> Any:
    method = method.upper()
    if read_only and method != "GET":
        raise ValueError("Server is in read-only mode; only GET requests are allowed.")
    cleaned_query = None
    if query:
        coerced = coerce_json(query)
        if isinstance(coerced, dict):
            cleaned_query = {k: coerce_json(v) for k, v in drop_none(coerced).items()}
    cleaned_body = coerce_json(body) if body is not None else None
    client = await get_client()
    return await client.request(method, path, params=cleaned_query, json=cleaned_body)


def register(mcp: FastMCP, *, read_only: bool) -> None:
    @mcp.tool(name="vrx_request", description=_DESCRIPTION)
    async def vrx_request(
        method: Annotated[str, Field(description="HTTP method, e.g. GET or POST")],
        path: Annotated[
            str, Field(description="Path relative to the API base, e.g. /endpoint/search")
        ],
        query: Annotated[
            Any | None, Field(default=None, description="Query params as an object")
        ] = None,
        body: Annotated[Any | None, Field(default=None, description="JSON request body")] = None,
    ) -> Any:
        return await _do_request(method, path, query, body, read_only=read_only)
