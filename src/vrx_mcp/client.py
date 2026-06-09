"""Async REST client for the Vicarius vRx External Data API."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from . import __version__
from .config import Config, get_config
from .errors import VrxAPIError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_MAX_RETRIES = 3
_MAX_RETRY_AFTER_SECONDS = 60.0


def _parse_retry_after(headers: httpx.Headers) -> float | None:
    """Seconds to wait before retrying, from vRx's rate-limit header or standard Retry-After.

    vRx returns the wait time in ``X-Rate-Limit-Retry-After-Seconds`` (an integer count of
    seconds); we prefer it and fall back to the standard ``Retry-After`` integer form.
    Returns None when neither is usable.
    """
    for name in ("X-Rate-Limit-Retry-After-Seconds", "Retry-After"):
        raw = headers.get(name)
        if raw is None:
            continue
        try:
            return max(0.0, float(raw.strip()))
        except (ValueError, AttributeError):
            continue
    return None


class VrxClient:
    """Thin async wrapper over the vRx REST API with one connection pool.

    Sends the configured auth header on every request. Retries transient failures
    (429/5xx/network) with full-jitter backoff, honoring the server's rate-limit wait hint.
    """

    def __init__(self, config: Config | None = None, transport: httpx.BaseTransport | None = None):
        self._config = config or get_config()
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._connect_lock = asyncio.Lock()

    async def __aenter__(self) -> VrxClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    async def connect(self) -> None:
        async with self._connect_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    base_url=self._config.base_url,
                    timeout=self._config.timeout,
                    transport=self._transport,
                    headers={
                        self._config.auth_header: self._config.api_key,
                        "Accept": "application/json",
                        "User-Agent": f"vrx-mcp/{__version__}",
                    },
                )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        if self._client is None:
            await self.connect()
        assert self._client is not None

        next_backoff: float | None = None
        for attempt in range(_MAX_RETRIES):
            if next_backoff is not None:
                logger.warning("Retry %d/%d — backing off %.2fs",
                               attempt, _MAX_RETRIES - 1, next_backoff)
                await asyncio.sleep(next_backoff)
                next_backoff = None

            try:
                response = await self._client.request(
                    method.upper(), path, params=params, json=json
                )
            except httpx.HTTPError as e:
                if attempt == _MAX_RETRIES - 1:
                    raise VrxAPIError(0, f"Network error: {e}") from e
                logger.warning("Network error on attempt %d: %s", attempt + 1, e)
                next_backoff = random.uniform(0, 2**attempt)
                continue

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                retry_after = _parse_retry_after(response.headers)
                next_backoff = (
                    min(retry_after, _MAX_RETRY_AFTER_SECONDS)
                    if retry_after is not None
                    else random.uniform(0, 2**attempt)
                )
                logger.warning("HTTP %d — will retry", response.status_code)
                continue

            if response.status_code >= 400:
                try:
                    body: Any = response.json()
                except ValueError:
                    body = response.text
                message = (
                    body.get("message") or body.get("error") or str(body)
                    if isinstance(body, dict)
                    else str(body)
                )
                raise VrxAPIError(response.status_code, message, body)

            try:
                return response.json()
            except ValueError:
                return response.text

        raise VrxAPIError(0, "Max retries exceeded")  # pragma: no cover


_client: VrxClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> VrxClient:
    global _client
    async with _client_lock:
        if _client is None:
            _client = VrxClient()
            await _client.connect()
    return _client


async def shutdown_client() -> None:
    global _client
    async with _client_lock:
        if _client is not None:
            await _client.close()
            _client = None
