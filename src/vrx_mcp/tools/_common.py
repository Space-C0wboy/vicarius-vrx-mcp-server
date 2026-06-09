"""Shared helpers used by every generated vRx tool and the escape hatch."""

from __future__ import annotations

import json
from typing import Any

from ..client import get_client


def drop_none(values: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``values`` without keys whose value is None (unset args)."""
    return {k: v for k, v in values.items() if v is not None}


def coerce_json(value: Any) -> Any:
    """Parse a JSON string encoding an object/array back into Python; pass through otherwise.

    MCP clients sometimes serialize complex args (bodies, searchQuerys) as JSON strings.
    Plain scalar strings (RSQL filters, ids) are returned unchanged.
    """
    if isinstance(value, str):
        stripped = value.lstrip()
        if stripped[:1] in ("{", "["):
            try:
                parsed = json.loads(stripped)
            except (ValueError, TypeError):
                return value
            if isinstance(parsed, (dict, list)):
                return parsed
    return value


async def execute_request(
    method: str,
    path_template: str,
    *,
    path_params: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> Any:
    """Interpolate path params, clean query/body, and dispatch via the shared client."""
    path = path_template.format(**(path_params or {}))
    cleaned_query = {k: coerce_json(v) for k, v in drop_none(query or {}).items()}
    cleaned_body = coerce_json(body) if body is not None else None
    client = await get_client()
    return await client.request(
        method, path, params=cleaned_query or None, json=cleaned_body
    )
