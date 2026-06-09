# Contributing

## Development

```bash
git clone https://github.com/Space-C0wboy/vicarius-vrx-mcp-server
cd vicarius-vrx-mcp-server
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
# .venv/bin/python -m pip install -e ".[dev]"      # macOS/Linux

.venv/Scripts/python -m pytest        # full suite (httpx fully mocked; no live calls)
.venv/Scripts/python -m ruff check .  # lint
```

## Regenerating tools

Tool modules under `src/vrx_mcp/tools/_generated/` are generated from the OpenAPI spec and
are **not hand-edited**. To change a tool, edit `scripts/generate_from_openapi.py` (its
`OVERRIDES` / `MUTATING_OVERRIDES` maps and classification helpers) and regenerate:

```bash
.venv/Scripts/python scripts/generate_from_openapi.py "Reference Material/api-docs.json"
```

Generation is deterministic — re-running it produces a byte-identical, reviewable diff. The
OpenAPI spec lives in `Reference Material/`, which is gitignored (vendor-proprietary).

## Releasing (PyPI)

Publishing is automated by `.github/workflows/release.yml` using **PyPI Trusted Publishing
(OIDC)** — no API token is stored. The workflow builds the sdist/wheel, runs `twine check`,
and uploads to PyPI when a **GitHub Release is published**, via the `pypi` environment.

The PyPI Trusted Publisher and the GitHub `pypi` environment are already configured
(publisher: project `vrx-mcp`, owner `Space-C0wboy`, repo `vicarius-vrx-mcp-server`,
workflow `release.yml`, environment `pypi`).

To cut a release:

1. Bump the version in `pyproject.toml` and `src/vrx_mcp/__init__.py`, update
   `CHANGELOG.md`, and commit.
2. Tag and push, e.g. `git tag v0.2.0 && git push origin v0.2.0`.
3. Create a GitHub Release for that tag. Publishing the Release triggers the workflow,
   which builds and uploads to PyPI.

Sanity-check the build locally before releasing:

```bash
.venv/Scripts/python -m build && .venv/Scripts/python -m twine check dist/*
```
