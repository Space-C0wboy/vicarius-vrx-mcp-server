"""Tool registry — wires every tool onto the FastMCP server."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import get_config
from . import request as request_tool
from ._generated import GENERATED_MODULES


def register_all(mcp: FastMCP) -> None:
    read_only = get_config().read_only
    for module in GENERATED_MODULES:
        module.register(mcp, read_only=read_only)
    request_tool.register(mcp, read_only=read_only)
