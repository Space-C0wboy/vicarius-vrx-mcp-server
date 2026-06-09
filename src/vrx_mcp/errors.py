"""Exception types for the Vicarius vRx MCP server."""

from __future__ import annotations

from typing import Any


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


class VrxAPIError(RuntimeError):
    """Raised on an HTTP error from the vRx API or a network failure.

    ``status_code`` is the HTTP status (or 0 for a network-level failure).
    ``body`` is the parsed error body when one was available.
    """

    def __init__(self, status_code: int, message: str, body: Any = None):
        super().__init__(f"vRx API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body
