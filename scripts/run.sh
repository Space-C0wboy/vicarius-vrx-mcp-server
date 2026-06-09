#!/usr/bin/env bash
set -euo pipefail
.venv/bin/python -m vrx_mcp.server "$@"
