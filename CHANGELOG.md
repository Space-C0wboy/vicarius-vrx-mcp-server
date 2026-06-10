# Changelog

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
