def test_version_present():
    import vrx_mcp

    assert isinstance(vrx_mcp.__version__, str)
    assert vrx_mcp.__version__
