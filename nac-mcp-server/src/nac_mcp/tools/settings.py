"""MCP tools for NAC settings."""
import json
from mcp.server.fastmcp import FastMCP
from nac_mcp.client import execute
from nac_mcp.types import build_scope


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_nac_settings(
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Get NAC Application Control settings for a scope.
        Returns default settings if none are configured.

        Args:
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        query = """
        query GetNACSettings($scope: ScopeSelectorInput) {
            nacSettings(scope: $scope) {
                fallbackBehavior enableApplicationControl inheritApplicationControl updatedBy updatedAt
            }
        }
        """
        data = execute(query, {"scope": build_scope(scope_type, scope_ids)})
        return json.dumps(data.get("nacSettings"), indent=2)

    @mcp.tool()
    def update_nac_settings(
        enable_application_control: bool,
        inherit_application_control: bool,
        fallback_behavior: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Configure NAC Application Control settings for a scope.

        Args:
            enable_application_control: Enable or disable Application Control.
            inherit_application_control: Inherit settings from parent scope.
            fallback_behavior: Default behavior when no rule matches — ALLOW, MONITOR, or BLOCK.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        mutation = """
        mutation UpdateNACSettings($input: NACSettingsInput!) {
            updateNACSettings(input: $input) {
                success id statusMessage
            }
        }
        """
        inp = {
            "scope": build_scope(scope_type, scope_ids),
            "enableApplicationControl": enable_application_control,
            "inheritApplicationControl": inherit_application_control,
            "fallbackBehavior": fallback_behavior,
        }
        data = execute(mutation, {"input": inp})
        return json.dumps(data.get("updateNACSettings"), indent=2)
