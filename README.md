# Vicarius vRx MCP Server

[![PyPI version](https://img.shields.io/pypi/v/vrx-mcp.svg)](https://pypi.org/project/vrx-mcp/)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://pypi.org/project/vrx-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/Space-C0wboy/vicarius-vrx-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/Space-C0wboy/vicarius-vrx-mcp-server/actions/workflows/ci.yml)
[![status: beta](https://img.shields.io/badge/status-beta-orange.svg)](#)

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the
**Vicarius vRx External Data API** (REST) to AI assistants. It provides **88 tools across 37
API domains** — Vulnerabilities/CVEs, Endpoints (Assets), Patches & Updates, Publishers &
Products, Tasks & Events, Automations & Scripts, Users, and more — plus a generic
`vrx_request` escape hatch for anything not covered by a dedicated tool. The tool set is
**generated directly from the vRx OpenAPI specification**, so it stays faithful to the real
API surface, and the generated output is deterministic and committed.

> [!IMPORTANT]
> **Unofficial project.** This is an independent, internally-built MCP server developed
> against Vicarius's published API documentation. It is **not** an official Vicarius product
> and is not affiliated with, endorsed by, or supported by Vicarius. "Vicarius" and "vRx"
> are trademarks of their respective owner. For official support of the vRx platform or the
> API itself, contact Vicarius directly.

> [!WARNING]
> **Beta software — not yet recommended for production.** This project is under active
> development. The tool surface may still change between versions, and not every endpoint has
> been exercised against every tenant/entitlement configuration.
>
> **This server can perform destructive actions against your vRx tenant.** Tools can delete
> assets and asset groups, create/update/delete users and invitations, modify automations and
> scan inputs, and update tasks. A hallucinated tool argument from your AI assistant could
> change your tenant configuration.
>
> **Recommended posture:**
> - **Run read-only first.** Set `VRX_READ_ONLY=true` to register only read tools and make
>   `vrx_request` reject any non-GET request. Lift it only when you need to write.
> - Use a vRx API key scoped to the **minimum permissions** your use case requires.
> - Review every mutating tool call before allowing execution. Claude Desktop requires
>   tool-call approval by default — keep that enabled.
> - Treat the API key with the same care as portal admin credentials.
> - The HTTP transport binds to `127.0.0.1` by default. Do not expose it to the public
>   internet without adding authentication.

## Tools

**88 tools across 37 API controllers** (59 read + 29 mutating), plus the `vrx_request` escape
hatch — **89 total in full mode, 60 in read-only mode** (mutating tools are not registered when
read-only). The table below groups the controllers into functional domains.

| Domain | Read | Write | Notable tools |
|--------|:----:|:-----:|---------------|
| **Vulnerabilities & CVEs** | 9 | 0 | `vulnerability_search`, `vulnerability_count`, `endpoint_vulnerability_filter`, `organization_endpoint_vulnerabilities_search`, `vulnerability_attack_vectors_search_by_fields`, `vulnerability_links_search_by_fields` |
| **Endpoints (Assets)** | 7 | 5 | `endpoint_search`, `endpoint_attributes_search`, `organization_endpoint_group_search`, `aggregation_search_group`, `endpoint_delete`, `organization_endpoint_group_insert` |
| **Patches & Updates** | 11 | 3 | `patch_management_patch`, `patch_management_cve_info`, `organization_endpoint_patch_patch_packages_filter`, `organization_endpoint_external_reference_external_references_search`, `patch_package_search_by_fields` |
| **Publishers, Products & OS** | 9 | 0 | `organization_publisher_products_search`, `organization_endpoint_publisher_product_versions_search`, `organization_publisher_operating_systems_search`, `operating_system_family_search_by_fields` |
| **Tasks & Events** | 10 | 7 | `task_event_filter`, `task_endpoints_event_filter`, `incident_event_filter`, `task_update`, `task_template_insert`, `automation_task_templates_insert` |
| **Automations & Scripts** | 9 | 9 | `automation_search`, `automations_automations`, `script_template_search`, `organization_scan_input_search`, `automation_delete`, `organization_scan_input_update` |
| **Users & Invitations** | 3 | 5 | `user_search`, `user_invitation_search`, `user_invitation_insert`, `user_invitation_update`, `user_invitation_delete` |
| **Utilities** | 1 | 0 | `date_get_current_date` |

See [`docs/ENDPOINTS.md`](docs/ENDPOINTS.md) for the **full tool ↔ method ↔ path mapping** (all
88 tools with their mutating flag).

**Highlights:**

- **Search tools** (`endpoint_search`, `vulnerability_search`, `organization_endpoint_group_search`, …)
  accept an **RSQL `q` filter** plus `from`/`size` paging — see [Querying](#querying).
- **Filter / count tools** (`*_filter`, `*_count`) cover event streams (incident events, task
  events) and counts for dashboards.
- **Aggregation tools** (`aggregation_group`, `aggregation_search_group`) power grouped/rollup
  queries (e.g. count of active CVEs grouped by vulnerability).
- **`vrx_request` escape hatch** issues an arbitrary request against the API for any endpoint
  without a dedicated tool. In read-only mode it rejects every non-GET method.
- **Read-only safety is enforced at two layers** — mutating tools are never registered in
  read-only mode, *and* `vrx_request` independently refuses mutations.

## Quick start

### Install

```bash
# with uv (recommended)
uv tool install vrx-mcp

# or with pip
pip install vrx-mcp
```

This installs the `vrx-mcp` console script. For development from source:

```bash
git clone https://github.com/Space-C0wboy/vicarius-vrx-mcp-server
cd vicarius-vrx-mcp-server
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
# .venv/bin/python -m pip install -e ".[dev]"      # macOS/Linux
```

### Getting an API key

1. In the vRx portal, go to **Settings**, select the **api** tag, then **Create Integration**.
2. Copy the generated API key — this is your `VRX_API_KEY`.
3. Your base URL is `https://<your-dashboard>.vicarius.cloud/vicarius-external-data-api`.

Requests authenticate with the **`vicarius-token`** header (the API key value); this server
sets it for you on every request.

### Configuration

Copy `.env.example` to `.env` and set:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VRX_API_KEY` | **yes** | — | Your vRx API key (Settings → api → Create Integration) |
| `VRX_BASE_URL` | **yes** | — | Full API base URL, e.g. `https://<dashboard>.vicarius.cloud/vicarius-external-data-api`. **No default** — the server fails fast if unset (no tenant is hardcoded) |
| `VRX_AUTH_HEADER` | no | `vicarius-token` | Header name carrying the API key |
| `VRX_READ_ONLY` | no | `false` | When true, no mutating tools are registered and `vrx_request` rejects non-GET requests |
| `VRX_TIMEOUT` | no | `60` | Request timeout in seconds |
| `LOG_LEVEL` | no | `INFO` | Logging level (logs go to stderr) |
| `MCP_HTTP_HOST` / `MCP_HTTP_PORT` | no | `127.0.0.1:8765` | HTTP transport bind |

### Run

- **stdio** (default, for Claude Desktop/Code): `vrx-mcp`
- **HTTP**: `vrx-mcp --transport http --port 8765`

## Querying

vRx search endpoints use **RSQL** in the `q` query parameter:

| Operator | Meaning | Example |
|----------|---------|---------|
| `==` | equals | `endpointName=='HOST01'` |
| `=in=(a,b,c)` | in list | `endpointId=in=(101,102,103)` |
| `=re='regex'` | regex match | `vulnerabilityExternalReference.externalReferenceExternalId=re='.*(cve-2024).*'` |
| `>` / `<` | compare | `analyticsEventCreatedAtNano>1682913600000000000` |

**Pagination:** every query takes `from` (offset) and `size`. **`size` ≤ 500** per request and
**`from` ≤ 10,000**. To page beyond offset 10,000, use **seek paging**: keep `from=0`, add a
`sort` (e.g. `-endpointId`), and add a `q` comparison on the last value seen
(e.g. `q=endpointId<525236`), repeating until the result is empty.

**Response envelope:** responses wrap results in a standard shape —
`serverResponseResult.serverResponseResultCode` (`"SUCCESS"`), `serverResponseCount` (total
matching records), and `serverResponseObject` (the array of records).

**Rate limits:** the API allows **60 queries / 60 seconds per organization scope** and returns
`HTTP 429` with an `X-Rate-Limit-Retry-After-Seconds` header when exceeded. The client
automatically retries 429s (and transient 5xx/network errors) with backoff, honoring that
header.

## Read-only mode

Set `VRX_READ_ONLY=true` to run the server safely against production. In this mode:

- **No mutating tools are registered** — only the 59 read tools (+ `vrx_request`) are exposed.
- **`vrx_request` rejects any non-GET method**, so it can only run read operations.

Read-only mode is strongly recommended for analyst-assistant, reporting, and dashboard use
cases where the model should never change tenant state. The shipped `.env.example` defaults to
read-only.

## Editor integration

### Claude Code

```bash
claude mcp add vrx \
  --env VRX_API_KEY=your-key-here \
  --env VRX_BASE_URL=https://your-dashboard.vicarius.cloud/vicarius-external-data-api \
  --env VRX_READ_ONLY=true \
  -- vrx-mcp
```

### Claude Desktop

Edit `claude_desktop_config.json`:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vrx": {
      "command": "vrx-mcp",
      "env": {
        "VRX_API_KEY": "your-key-here",
        "VRX_BASE_URL": "https://your-dashboard.vicarius.cloud/vicarius-external-data-api",
        "VRX_READ_ONLY": "true"
      }
    }
  }
}
```

Restart Claude Desktop, then confirm `vrx` appears in the tools menu.

## Example prompts

- *"List the first 100 assets in vRx."* → `endpoint_search` (`from=0`, `size=100`).
- *"Find the asset named HOST01."* → `endpoint_search` (`q=endpointName=='HOST01'`).
- *"Show me all Critical CVEs."* → `vulnerability_search`
  (`q=vulnerabilitySensitivityLevel.sensitivityLevelName=='Critical'`).
- *"Which assets are affected by CVE-2024-3094?"* → `vulnerability_search` to resolve the CVE,
  then `endpoint_search` with a `searchQuerys` join body on `OrganizationEndpointVulnerabilities`.
- *"List endpoints with critical missing patches."* →
  `organization_endpoint_external_reference_external_references_search`
  (`q=...patchSensitivityLevel.sensitivityLevelName=='Critical'`).
- *"Get attack vectors and links for a vulnerability."* → `vulnerability_attack_vectors_search_by_fields`
  / `vulnerability_links_search_by_fields` (`q=vulnerabilityId==<id>`).
- *"Show the recent event log."* → `incident_event_filter` (sort + `analyticsEventCreatedAtNano` range).
- *"Count active CVEs grouped by vulnerability."* → `aggregation_search_group`.
- *"Call an endpoint I don't have a tool for."* → `vrx_request` (`method`, `path`, `query`, `body`).

## How tools are generated

The tool modules are generated from the vRx OpenAPI specification:

```bash
python scripts/generate_from_openapi.py "Reference Material/api-docs.json"
```

This regenerates the modules under `src/vrx_mcp/tools/_generated/` and the catalog at
`docs/ENDPOINTS.md`. The generated files are **not hand-edited** — to change a tool, edit the
generator (its `OVERRIDES` / `MUTATING_OVERRIDES` maps) and regenerate. Generation is
deterministic, so re-running it produces a byte-identical, reviewable diff.

The OpenAPI spec and other vRx reference material live in the **`Reference Material/`**
directory, which is **gitignored** (vendor/customer-proprietary material, not redistributed).

Key generator behavior:
- Operations are grouped by OpenAPI controller tag into one module per domain.
- Redundant **GET/POST search twins** are collapsed to a single tool (the POST/body form).
- Each operation is classified **mutating** (`PUT`/`DELETE`, or a non-search `POST`) or
  **read** (`GET`, or a search-style `POST`); mutating tools are hidden in read-only mode.

## Development

```bash
.venv/Scripts/python -m pytest        # full suite (httpx fully mocked; no live calls)
.venv/Scripts/python -m ruff check .  # lint
.venv/Scripts/python scripts/generate_from_openapi.py "Reference Material/api-docs.json"  # regenerate
```

CI runs ruff + pytest on Python 3.10 / 3.11 / 3.12 (see `.github/workflows/ci.yml`).

## Releasing (PyPI)

Publishing is automated via `.github/workflows/release.yml` using **PyPI Trusted
Publishing (OIDC)** — no API token is stored. The workflow builds the sdist/wheel, runs
`twine check`, and publishes when a **GitHub Release is published**.

**One-time setup (PyPI side):**
1. On [PyPI](https://pypi.org/manage/account/publishing/), add a **Trusted Publisher**.
   Because the project doesn't exist on PyPI yet, add it as a *pending* publisher:
   - PyPI Project Name: `vrx-mcp`
   - Owner: `Space-C0wboy`
   - Repository: `vicarius-vrx-mcp-server`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
2. In GitHub repo **Settings → Environments**, create an environment named `pypi`
   (optionally add required-reviewer protection for a manual approval gate).

**Cutting a release:**
1. Bump the version in `pyproject.toml` and `src/vrx_mcp/__init__.py`, update
   `CHANGELOG.md`, commit.
2. Tag and push: `git tag v0.1.0 && git push origin v0.1.0`.
3. Create a GitHub Release for that tag. Publishing the Release triggers the workflow,
   which uploads to PyPI.

> [!NOTE]
> Publishing to public PyPI makes the package source publicly downloadable, even though
> this GitHub repository is private. Use a private index instead if the code must stay
> internal.

Build locally to sanity-check before releasing:

```bash
.venv/Scripts/python -m build && .venv/Scripts/python -m twine check dist/*
```

## License

[MIT](LICENSE)

## Support

This is an unofficial, internal project. For vRx platform or API questions, contact Vicarius
directly. For issues with this MCP server, open an issue on the
[GitHub repository](https://github.com/Space-C0wboy/vicarius-vrx-mcp-server/issues).
