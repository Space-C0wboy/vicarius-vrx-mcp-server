"""Vicarius vRx MCP server — entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys

from fastmcp import FastMCP

from .client import shutdown_client
from .config import ConfigError, get_config
from .tools import register_all

_INSTRUCTIONS = (
    "MCP server for the Vicarius vRx External Data API (REST). Tools are grouped by domain "
    "(vulnerability, endpoint, patch, task, automation, organization, etc.). Search tools "
    "use RSQL in the `q` param: == (equals), =in=(a,b), =re='regex', > / < (compare). "
    "Pagination: size<=500, from<=10000; beyond 10000 use seek paging (sort + a q comparison "
    "on the last value). Use `vrx_request` for endpoints without a dedicated tool. With "
    "VRX_READ_ONLY=true, mutating tools are hidden and vrx_request rejects non-GET calls."
)


def build_server() -> FastMCP:
    config = get_config()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    mcp = FastMCP(name="vrx-mcp", instructions=_INSTRUCTIONS)
    register_all(mcp)
    return mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vrx-mcp")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)

    try:
        mcp = build_server()
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    config = get_config()
    try:
        if args.transport == "stdio":
            mcp.run(transport="stdio")
        else:
            mcp.run(
                transport="http",
                host=args.host or config.http_host,
                port=args.port or config.http_port,
            )
    finally:
        import asyncio

        try:
            asyncio.run(shutdown_client())
        except RuntimeError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
