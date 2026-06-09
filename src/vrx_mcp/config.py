"""Server configuration, loaded once and validated from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .errors import ConfigError

load_dotenv()

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str
    auth_header: str
    read_only: bool
    timeout: float
    log_level: str
    http_host: str
    http_port: int

    @classmethod
    def from_env(cls) -> Config:
        api_key = os.getenv("VRX_API_KEY", "").strip()
        if not api_key:
            raise ConfigError(
                "VRX_API_KEY is required. Set it in your environment or .env file."
            )

        base_url = os.getenv("VRX_BASE_URL", "").strip().rstrip("/")
        if not base_url:
            raise ConfigError(
                "VRX_BASE_URL is required (e.g. "
                "https://<dashboard>.vicarius.cloud/vicarius-external-data-api). "
                "Set it in your environment or .env file."
            )
        if not base_url.startswith(("http://", "https://")):
            raise ConfigError(
                f"VRX_BASE_URL must start with http:// or https:// (got {base_url!r})"
            )

        auth_header = os.getenv("VRX_AUTH_HEADER", "vicarius-token").strip() or "vicarius-token"
        read_only = os.getenv("VRX_READ_ONLY", "false").strip().lower() in _TRUTHY

        try:
            timeout = float(os.getenv("VRX_TIMEOUT", "60"))
        except ValueError as e:
            raise ConfigError(f"VRX_TIMEOUT must be a number: {e}") from e

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        http_host = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
        try:
            http_port = int(os.getenv("MCP_HTTP_PORT", "8765"))
        except ValueError as e:
            raise ConfigError(f"MCP_HTTP_PORT must be an integer: {e}") from e

        return cls(
            api_key=api_key,
            base_url=base_url,
            auth_header=auth_header,
            read_only=read_only,
            timeout=timeout,
            log_level=log_level,
            http_host=http_host,
            http_port=http_port,
        )


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config_cache() -> None:
    global _config
    _config = None
