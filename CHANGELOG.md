# Changelog

## 0.1.2

- Fix: replace `hashlib.md5` with `sha256` for tool-name deduplication hash (Snyk CWE-916).
- Fix: harden `generate_from_openapi.py` CLI argument handling — validate file extension before
  constructing the path, call `.resolve()` to canonicalize, and check file existence; refactored
  `generate()` to accept a parsed spec dict rather than a raw path (Snyk CWE-23).
- Fix: replace hardcoded placeholder string in test helper with `os.environ.get("VRX_API_KEY", "dummy")`
  to avoid static-analysis false positives on hardcoded secrets (Snyk CWE-547).
- Add `.snyk` policy file documenting the suppressed path-traversal false positive on the
  developer-only codegen script.

## 0.1.1

- Fix: two generated tool names exceeded the MCP 64-character tool-name limit
  (`organization_endpoint_publisher_operating_systems_locate_object_position`,
  `organization_endpoint_external_reference_external_references_search`), which prevented
  the server from loading in some MCP clients. They are renamed to
  `org_endpoint_publisher_os_locate_position` and `org_endpoint_external_references_search`,
  and the generator now enforces the 64-char limit for every tool name.

## 0.1.0

- Initial release: MCP server for the Vicarius vRx External Data API.
- Tools generated from the OpenAPI spec across all controller domains.
- `vrx_request` escape hatch; read-only mode; rate-limit-aware retries.
