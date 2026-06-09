import pytest

from vrx_mcp.errors import ConfigError, VrxAPIError


def test_config_error_is_runtime_error():
    assert issubclass(ConfigError, RuntimeError)


def test_api_error_carries_status_and_message():
    err = VrxAPIError(404, "not found", {"detail": "x"})
    assert err.status_code == 404
    assert err.body == {"detail": "x"}
    assert "404" in str(err)
    assert "not found" in str(err)


def test_api_error_body_optional():
    err = VrxAPIError(0, "network down")
    assert err.body is None
    with pytest.raises(VrxAPIError):
        raise err
