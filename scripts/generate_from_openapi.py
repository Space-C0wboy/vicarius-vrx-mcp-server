"""Generate FastMCP tool modules from the Vicarius vRx OpenAPI spec.

Reads an OpenAPI 3 document and emits one module per controller tag into
src/vrx_mcp/tools/_generated/, plus docs/ENDPOINTS.md. Output is deterministic
(sorted, LF newlines) so it can be committed and reviewed in diffs.

Usage:
    python scripts/generate_from_openapi.py ["Reference Material/api-docs.json"]
"""

from __future__ import annotations

import json
import keyword
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SPEC = Path("Reference Material/api-docs.json")
DEFAULT_OUT_DIR = Path("src/vrx_mcp/tools/_generated")
DEFAULT_DOC = Path("docs/ENDPOINTS.md")

# When loaded via importlib (e.g. tests using spec_from_file_location without
# registering in sys.modules), @dataclass with `from __future__ import annotations`
# fails resolving cls.__module__ in sys.modules. Register a module object whose
# __dict__ IS this module's globals so dataclass field resolution succeeds.
if __name__ not in sys.modules:
    import types as _types

    _self = _types.ModuleType(__name__)
    _self.__dict__.update(globals())
    sys.modules[__name__] = _self

_HTTP_METHODS = ("get", "post", "put", "delete", "patch")
_SCALAR_ANNOT = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}

# Search-style POSTs are reads, not writes. Match by path suffix or summary.
_SEARCH_PATH_RE = re.compile(r"/(search|searchByFields|filter|searchGroup|group)$")
_SEARCH_SUMMARIES = {"returns events", "get object by connection"}

# Curated descriptions for high-traffic domains (seeded from the portal API library).
OVERRIDES: dict[str, str] = {
    "vulnerability_search": (
        "Search vulnerabilities/CVEs. RSQL `q` filter, e.g. "
        "q=vulnerabilitySensitivityLevel.sensitivityLevelName=='Critical'. "
        "size<=500, from<=10000."
    ),
    "endpoint_search": (
        "Search endpoints (assets). RSQL `q` filter, e.g. q=endpointName=='HOST01'. "
        "size<=500, from<=10000; use sort + seek paging beyond 10000."
    ),
}

# Correct any misclassified mutating/non-mutating operations: tool_name -> mutating bool.
MUTATING_OVERRIDES: dict[str, bool] = {}


@dataclass
class Operation:
    domain: str
    tool_name: str
    method: str
    path: str
    summary: str
    mutating: bool
    path_params: list[dict] = field(default_factory=list)
    query_params: list[dict] = field(default_factory=list)
    has_body: bool = False


@dataclass
class Domain:
    module_name: str
    operations: list[Operation]


def _snake(name: str) -> str:
    name = name.replace("-controller-impl", "")
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return name.lower().strip("_")


def safe_param_name(name: str) -> str:
    """Map a wire param name to a valid, non-keyword Python identifier."""
    py = re.sub(r"[^0-9a-zA-Z_]", "_", name)
    if not py or py[0].isdigit():
        py = "p_" + py
    if keyword.iskeyword(py):
        py = py + "_"
    return py


def _action_from_path(path: str) -> str:
    segs = [s for s in path.split("/") if s and not s.startswith("{")]
    return _snake(segs[-1]) if segs else "root"


def _is_search(path: str, summary: str) -> bool:
    if _SEARCH_PATH_RE.search(path):
        return True
    return summary.strip().lower() in _SEARCH_SUMMARIES


def _classify_mutating(method: str, path: str, summary: str) -> bool:
    if method in ("put", "delete", "patch"):
        return True
    if method == "post":
        return not _is_search(path, summary)
    return False  # get


def collect_domains(spec: dict) -> list[Domain]:
    """Parse the spec into Domains of deduped, classified Operations (sorted, deterministic)."""
    raw: dict[str, list[Operation]] = {}
    # path -> {method: operation dict} to detect GET/POST search twins.
    for path in sorted(spec.get("paths", {})):
        methods = spec["paths"][path]
        present = {m: methods[m] for m in _HTTP_METHODS if m in methods}

        # GET/POST search twin: same path, both verbs, search-style -> keep POST only.
        if "get" in present and "post" in present:
            g, p = present["get"], present["post"]
            if _is_search(path, g.get("summary", "")) and _is_search(path, p.get("summary", "")):
                del present["get"]

        for method in sorted(present):
            op = present[method]
            tag = (op.get("tags") or ["untagged"])[0]
            module = _snake(tag)
            summary = op.get("summary", "") or ""
            tool_name = f"{module}_{_action_from_path(path)}"
            params = op.get("parameters", []) or []
            operation = Operation(
                domain=module,
                tool_name=tool_name,
                method=method.upper(),
                path=path,
                summary=summary,
                mutating=_classify_mutating(method, path, summary),
                path_params=[x for x in params if x.get("in") == "path"],
                query_params=[x for x in params if x.get("in") == "query"],
                has_body="requestBody" in op,
            )
            raw.setdefault(module, []).append(operation)

    # Resolve duplicate tool names within a domain with deterministic suffixes.
    domains: list[Domain] = []
    for module in sorted(raw):
        ops = sorted(raw[module], key=lambda o: (o.path, o.method))
        seen: dict[str, int] = {}
        for o in ops:
            if o.tool_name in seen:
                seen[o.tool_name] += 1
                o.tool_name = f"{o.tool_name}_{seen[o.tool_name]}"
            else:
                seen[o.tool_name] = 0
        for o in ops:
            if o.tool_name in MUTATING_OVERRIDES:
                o.mutating = MUTATING_OVERRIDES[o.tool_name]
        domains.append(Domain(module_name=module, operations=ops))
    return domains


def _annot(schema: dict) -> str:
    return _SCALAR_ANNOT.get((schema or {}).get("type"), "Any")


def _py_default_param(py_name: str, annot: str, desc: str) -> str:
    return (
        f"        {py_name}: Annotated[{annot} | None, "
        f"Field(default=None, description={json.dumps(desc)})] = None,"
    )


def _emit_tool(op: Operation) -> str:
    lines: list[str] = []
    desc = OVERRIDES.get(
        op.tool_name, f"{op.domain} · {op.method} {op.path} — {op.summary}".strip(" —")
    )
    lines.append(f'    @mcp.tool(name={json.dumps(op.tool_name)}, description={json.dumps(desc)})')
    sig = [f"    async def {op.tool_name}("]

    # Path params: required, no default.
    path_map: list[str] = []
    for p in op.path_params:
        py = safe_param_name(p["name"])
        annot = _annot(p.get("schema", {}))
        sig.append(f"        {py}: Annotated[{annot}, Field(description={json.dumps('path param ' + p['name'])})],")
        path_map.append(f"{json.dumps(p['name'])}: {py}")

    # Query params: optional.
    query_map: list[str] = []
    for p in op.query_params:
        py = safe_param_name(p["name"])
        annot = _annot(p.get("schema", {}))
        sig.append(_py_default_param(py, annot, f"query param {p['name']} ({annot})"))
        query_map.append(f"{json.dumps(p['name'])}: {py}")

    # Body param.
    body_arg = "None"
    if op.has_body:
        sig.append(_py_default_param("body", "Any", "JSON request body"))
        body_arg = "body"

    sig.append("    ) -> Any:")
    lines.extend(sig)
    path_params_literal = "{" + ", ".join(path_map) + "}"
    query_literal = "{" + ", ".join(query_map) + "}"
    lines.append(
        f"        return await execute_request({json.dumps(op.method)}, "
        f"{json.dumps(op.path)}, path_params={path_params_literal}, "
        f"query={query_literal}, body={body_arg})"
    )
    return "\n".join(lines)


_MODULE_HEADER = '''"""Vicarius vRx MCP tools for domain: {domain}.

GENERATED by scripts/generate_from_openapi.py — DO NOT EDIT BY HAND.
Edit the generator (its OVERRIDES / MUTATING_OVERRIDES maps) and regenerate.
"""

from __future__ import annotations

from typing import {typing_imports}

from fastmcp import FastMCP
{pydantic_import}from .._common import execute_request


def register(mcp: FastMCP, *, read_only: bool) -> None:
'''


def _emit_module(domain: Domain) -> str:
    non_mut = [o for o in domain.operations if not o.mutating]
    mut = [o for o in domain.operations if o.mutating]
    # Only import Annotated/Field when some operation actually declares params or a body;
    # otherwise ruff (F401) flags the unused imports in param-less domains.
    needs_field = any(
        o.path_params or o.query_params or o.has_body for o in domain.operations
    )
    typing_imports = "Annotated, Any" if needs_field else "Any"
    pydantic_import = "from pydantic import Field\n\n" if needs_field else "\n"
    header = _MODULE_HEADER.format(
        domain=domain.module_name,
        typing_imports=typing_imports,
        pydantic_import=pydantic_import,
    )
    body = [header]
    body.append("    # --- Non-mutating tools (always registered) ---")
    if non_mut:
        body.append("\n\n".join(_emit_tool(o) for o in non_mut))
    else:
        body.append("    pass")
    if mut:
        body.append("\n    # --- Mutating tools (registered only when not read_only) ---")
        body.append("    if not read_only:")
        # Indent mutating tools one extra level under the if-block.
        for o in mut:
            body.append("\n".join("    " + ln if ln else ln for ln in _emit_tool(o).split("\n")))
    return "\n".join(body) + "\n"


def _emit_init(domains: list[Domain]) -> str:
    names = [d.module_name for d in domains]
    lines = ['"""GENERATED — DO NOT EDIT. Aggregates every generated domain module."""', ""]
    lines.append("from __future__ import annotations")
    lines.append("")
    # Parenthesized multiline import keeps ruff's isort (I001) happy.
    lines.append("from . import (")
    for n in names:
        lines.append(f"    {n},")
    lines.append(")")
    lines.append("")
    joined = ", ".join(names)
    lines.append(f"GENERATED_MODULES = [{joined}]")
    lines.append("")
    return "\n".join(lines)


def _emit_doc(domains: list[Domain]) -> str:
    lines = ["# vRx MCP Tool Catalog", "", "| Tool | Method | Path | Mutating |", "|------|--------|------|:--------:|"]
    for d in domains:
        for o in d.operations:
            lines.append(f"| `{o.tool_name}` | {o.method} | `{o.path}` | {'yes' if o.mutating else 'no'} |")
    return "\n".join(lines) + "\n"


def generate(spec_path: Path, out_dir: Path, doc_path: Path) -> None:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    domains = collect_domains(spec)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for d in domains:
        (out_dir / f"{d.module_name}.py").write_text(_emit_module(d), encoding="utf-8", newline="\n")
    (out_dir / "__init__.py").write_text(_emit_init(domains), encoding="utf-8", newline="\n")
    Path(doc_path).parent.mkdir(parents=True, exist_ok=True)
    Path(doc_path).write_text(_emit_doc(domains), encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    spec_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_SPEC
    generate(spec_path, DEFAULT_OUT_DIR, DEFAULT_DOC)
    print(f"Generated tools from {spec_path} into {DEFAULT_OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
