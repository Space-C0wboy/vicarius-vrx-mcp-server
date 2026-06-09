# Vicarius vRx MCP Server

An unofficial [Model Context Protocol](https://modelcontextprotocol.io) server exposing the
**Vicarius vRx External Data API** to AI assistants as typed tools, plus a generic
`vrx_request` escape hatch. Built with Python + FastMCP.

> **Unofficial project.** Not affiliated with or endorsed by Vicarius. Treat your API key
> like a credential. Start in read-only mode.

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VRX_API_KEY` | **yes** | — | Portal API key (Settings → api tag → Create Integration) |
| `VRX_BASE_URL` | **yes** | — | Full API base URL for your tenant, e.g. `https://<dashboard>.vicarius.cloud/vicarius-external-data-api` (no default) |
| `VRX_AUTH_HEADER` | no | `vicarius-token` | Header name carrying the API key |
| `VRX_READ_ONLY` | no | `false` | Hide mutating tools; `vrx_request` rejects non-GET |
| `VRX_TIMEOUT` | no | `60` | Request timeout (seconds) |
| `LOG_LEVEL` | no | `INFO` | Logging level |
| `MCP_HTTP_HOST` / `MCP_HTTP_PORT` | no | `127.0.0.1:8765` | HTTP transport bind |

## Run

- stdio (default): `vrx-mcp`
- HTTP: `vrx-mcp --transport http --port 8765`

## Querying

Search tools use **RSQL** in the `q` param: `==`, `=in=(a,b)`, `=re='regex'`, `>`, `<`.
Pagination: `size` ≤ 500, `from` (offset) ≤ 10000; beyond 10000, use seek paging
(`sort` + a `q` comparison on the last-seen value). The API rate-limits to 60 queries / 60s
per org; the client retries 429s using the `X-Rate-Limit-Retry-After-Seconds` hint.

## Development

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest          # full suite (httpx mocked)
.venv/Scripts/python -m ruff check .
.venv/Scripts/python scripts/generate_from_openapi.py "Reference Material/api-docs.json"
```

Generated tool modules under `src/vrx_mcp/tools/_generated/` are **not hand-edited** — change
the generator and regenerate.
