import pytest

from vrx_mcp.config import Config, get_config, reset_config_cache
from vrx_mcp.errors import ConfigError


@pytest.fixture(autouse=True)
def _clear(monkeypatch):
    # Strip every VRX_* var so each test controls the environment.
    for var in ("VRX_API_KEY", "VRX_BASE_URL", "VRX_AUTH_HEADER",
                "VRX_READ_ONLY", "VRX_TIMEOUT", "LOG_LEVEL",
                "MCP_HTTP_HOST", "MCP_HTTP_PORT"):
        monkeypatch.delenv(var, raising=False)
    reset_config_cache()
    yield
    reset_config_cache()


_BASE = "https://mcleod.vicarius.cloud/vicarius-external-data-api"


def test_requires_api_key(monkeypatch):
    monkeypatch.setenv("VRX_BASE_URL", _BASE)
    with pytest.raises(ConfigError):
        Config.from_env()


def test_requires_base_url(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_defaults(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "secret")
    monkeypatch.setenv("VRX_BASE_URL", _BASE)
    cfg = Config.from_env()
    assert cfg.api_key == "secret"
    assert cfg.base_url == _BASE
    assert cfg.auth_header == "vicarius-token"
    assert cfg.read_only is False
    assert cfg.timeout == 60.0
    assert cfg.http_host == "127.0.0.1"
    assert cfg.http_port == 8765


def test_base_url_trailing_slash_trimmed(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", "https://x.vicarius.cloud/vicarius-external-data-api/")
    assert Config.from_env().base_url == "https://x.vicarius.cloud/vicarius-external-data-api"


def test_base_url_must_be_http(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", "ftp://nope")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_read_only_truthy(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", _BASE)
    monkeypatch.setenv("VRX_READ_ONLY", "TRUE")
    assert Config.from_env().read_only is True


def test_bad_timeout(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", _BASE)
    monkeypatch.setenv("VRX_TIMEOUT", "abc")
    with pytest.raises(ConfigError):
        Config.from_env()


def test_get_config_is_cached(monkeypatch):
    monkeypatch.setenv("VRX_API_KEY", "k")
    monkeypatch.setenv("VRX_BASE_URL", _BASE)
    assert get_config() is get_config()
