"""MCP tools for NAC rule metadata and filter counts."""
import json
from mcp.server.fastmcp import FastMCP
from nac_mcp.client import execute
from nac_mcp.types import build_scope


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_nac_rule_column_metadata() -> str:
        """
        Get metadata for all NAC rule columns — field IDs, supported filter types, and sortability.
        Useful for building dynamic filter/sort UIs or understanding available filter fields.
        """
        query = """
        query {
            nacRuleColumnMetadata {
                fieldId sortable groupable filterTypes enumValues
            }
        }
        """
        data = execute(query)
        return json.dumps(data.get("nacRuleColumnMetadata"), indent=2)

    @mcp.tool()
    def get_nac_rule_filters_count(
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
        include_parents: bool = False,
        filter_field: str | None = None,
        filter_value: str | None = None,
    ) -> str:
        """
        Get faceted value counts for NAC rule filter fields.
        Useful for showing filter options with counts (e.g. osType: MACOS=12, WINDOWS=8).

        Args:
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
            include_parents: Include rules from parent scopes.
            filter_field: Optional field to pre-filter by.
            filter_value: Optional value for the pre-filter (fulltext match).
        """
        query = """
        query GetFiltersCount($scope: ScopeSelectorInput, $filter: [CommonFilterInput], $includeParents: Boolean) {
            nacRuleFiltersCount(scope: $scope, filterInput: $filter, includeParents: $includeParents) {
                data {
                    fieldId hasNextPage
                    values { value label count }
                }
            }
        }
        """
        variables: dict = {
            "scope": build_scope(scope_type, scope_ids),
            "includeParents": include_parents,
        }
        if filter_field and filter_value:
            variables["filter"] = [{"fieldId": filter_field, "match": {"value": filter_value}}]

        data = execute(query, variables)
        return json.dumps(data.get("nacRuleFiltersCount"), indent=2)
