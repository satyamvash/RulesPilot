"""MCP tools for NAC rule CRUD and validation."""
import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from nac_mcp.client import execute
from nac_mcp.types import build_scope, build_conditions, build_pagination


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def nac_health_check() -> str:
        """Check if the NAC Config Service is running."""
        data = execute("query { nacHealthCheck }")
        return data.get("nacHealthCheck", "")

    @mcp.tool()
    def get_nac_rule(
        rule_id: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Fetch a single NAC rule by ID.

        Args:
            rule_id: Numeric rule ID as a string.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        query = """
        query GetNACRule($id: ID!, $scope: ScopeSelectorInput) {
            nacRule(id: $id, scope: $scope) {
                id ruleName description
                scope { scopeId scopeLevel }
                osType behavior propagation label
                createdAt createdBy
                parameters { publisher path signer sha256 process parentProcess parentLabel }
                exceptions { publisher path signer sha256 process parentProcess parentLabel }
            }
        }
        """
        data = execute(query, {"id": rule_id, "scope": build_scope(scope_type, scope_ids)})
        return json.dumps(data.get("nacRule"), indent=2)

    @mcp.tool()
    def list_nac_rules(
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
        size: int = 50,
        cursor: str | None = None,
        direction: str = "FORWARD",
        include_parents: bool = False,
        filter_field: str | None = None,
        filter_value: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "ASC",
    ) -> str:
        """
        List NAC rules with pagination, optional filtering by a single field, and optional sorting.

        Args:
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
            size: Page size (max 1000, default 50). Defaults to 50
            cursor: Pagination cursor from a previous response. Defaults to None
            direction: FORWARD or BACKWARD. Defaults to FORWARD
            include_parents: Whether to include rules from parent scopes. Defaults to true
            filter_field: Field name to filter on (e.g. ruleName, osType, behavior). Defaults to None
            filter_value: String value to match (fulltext match). Defaults to None
            sort_by: Field to sort by (e.g. ruleName, behavior, createdBy). Defaults to None
            sort_order: ASC or DESC. Defaults to ASC
        """
        query = """
        query ListNACRules(
            $scope: ScopeSelectorInput,
            $pagination: NACPaginationInput,
            $filter: [CommonFilterInput],
            $sort: [CommonSortInput],
            $includeParents: Boolean
        ) {
            nacRules(scope: $scope, paginationInput: $pagination, filterInput: $filter, sortInput: $sort, includeParents: $includeParents) {
                totalCount
                pageInfo { startCursor endCursor hasNextPage hasPreviousPage }
                edges {
                    cursor
                    node {
                        id ruleName description behavior osType propagation label
                        scope { scopeId scopeLevel }
                        createdAt createdBy
                        parameters { publisher path signer sha256 process parentProcess parentLabel }
                    }
                }
            }
        }
        """
        filter_input = None
        if filter_field and filter_value:
            filter_input = [{"fieldId": filter_field, "match": {"value": filter_value}}]

        sort_input = None
        if sort_by:
            sort_input = [{"by": sort_by, "order": sort_order}]

        variables: dict[str, Any] = {
            "scope": build_scope(scope_type, scope_ids),
            "pagination": build_pagination(size, cursor, direction),
            "includeParents": include_parents,
        }
        if filter_input:
            variables["filter"] = filter_input
        if sort_input:
            variables["sort"] = sort_input

        data = execute(query, variables)
        return json.dumps(data.get("nacRules"), indent=2)

    @mcp.tool()
    def get_nac_rule_change_log(
        rule_id: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Get the audit change log for a NAC rule.

        Args:
            rule_id: Numeric rule ID as a string.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        query = """
        query GetNACRuleChangeLog($id: ID!, $scope: ScopeSelectorInput) {
            nacRuleChangeLog(id: $id, scope: $scope) {
                ruleId createdBy createdAt
                changeLog { version updatedBy updatedAt }
            }
        }
        """
        data = execute(query, {"id": rule_id, "scope": build_scope(scope_type, scope_ids)})
        return json.dumps(data.get("nacRuleChangeLog"), indent=2)

    @mcp.tool()
    def validate_nac_rule(
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
        rule_name: str | None = None,
        behavior: str | None = None,
        os_type: list[str] | None = None,
        publisher: str | None = None,
        path: str | None = None,
        signer: str | None = None,
        sha256: str | None = None,
        process: str | None = None,
        parent_process: str | None = None,
        parent_label: str | None = None,
        rule_id: str | None = None,
    ) -> str:
        """
        Validate NAC rule fields without persisting. All fields are optional — only provided fields are validated.
        Useful for real-time form validation.

        Args:
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
            rule_name: Rule name to validate.
            behavior: ALLOW, MONITOR, or BLOCK.
            os_type: List of OS types: MACOS, WINDOWS.
            publisher: Publisher condition to validate.
            path: Path condition to validate.
            signer: Signer condition to validate.
            sha256: SHA-256 hash to validate.
            process: Process name to validate.
            parent_process: Parent process to validate.
            parent_label: Parent label ID to validate.
            rule_id: Existing rule ID (for update context).
        """
        query = """
        query ValidateNACRule($input: NACRuleValidationInput!) {
            nacValidateRule(input: $input) {
                success id statusMessage
                validationErrors {
                    ruleName { code message }
                    behavior { code message }
                    osType { code message }
                    parameters { publisher { code message } path { code message } signer { code message } sha256 { code message } process { code message } parentProcess { code message } parentLabel { code message } }
                    unmapped { code message }
                }
            }
        }
        """
        inp: dict[str, Any] = {"scope": build_scope(scope_type, scope_ids)}
        if rule_id:
            inp["id"] = rule_id
        if rule_name is not None:
            inp["ruleName"] = rule_name
        if behavior is not None:
            inp["behavior"] = behavior
        if os_type is not None:
            inp["osType"] = os_type

        conditions = build_conditions(publisher, path, signer, sha256, process, parent_process, parent_label)
        if conditions:
            inp["parameters"] = conditions

        data = execute(query, {"input": inp})
        return json.dumps(data.get("nacValidateRule"), indent=2)

    @mcp.tool()
    def create_or_update_nac_rule(
        rule_name: str,
        behavior: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
        publisher: str | None = None,
        path: str | None = None,
        signer: str | None = None,
        sha256: str | None = None,
        process: str | None = None,
        parent_process: str | None = None,
        parent_label: str | None = None,
        description: str | None = None,
        os_type: list[str] | None = None,
        propagation: bool | None = None,
        label: str | None = None,
        rule_id: str | None = None,
        exceptions_json: str | None = None,
    ) -> str:
        """
        Create a new NAC rule (if rule_id is omitted) or update an existing one (if rule_id is provided).
        Only rules with source=SINGLE can be updated.

        Args:
            rule_name: Name for the rule.
            behavior: ALLOW, MONITOR, or BLOCK.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
            publisher: Publisher condition. Optional parameter
            path: Path condition. Optional parameter
            signer: Signer condition. Optional parameter
            sha256: SHA-256 hash condition. Optional parameter
            process: Process name condition. Optional parameter
            parent_process: Parent process condition. Optional parameter
            parent_label: Parent label ID. Optional parameter
            description: Optional description.
            os_type: List of MACOS / WINDOWS. 
            propagation: Whether rule propagates to child scopes. Defaults to true
            label: Label string.
            rule_id: Provide to update an existing rule; omit to create.
            exceptions_json: JSON array of NACRuleConditionsInput objects for exceptions.
        """
        mutation = """
        mutation CreateOrUpdateNACRule($input: NACRuleInput!) {
            updateNACSingleRule(input: $input) {
                success id statusMessage
                validationErrors {
                    ruleName { code message }
                    behavior { code message }
                    parameters { publisher { code message } path { code message } sha256 { code message } }
                    unmapped { code message }
                }
            }
        }
        """
        inp: dict[str, Any] = {
            "scope": build_scope(scope_type, scope_ids),
            "ruleName": rule_name,
            "behavior": behavior,
            "parameters": build_conditions(publisher, path, signer, sha256, process, parent_process, parent_label),
        }
        if rule_id:
            inp["id"] = rule_id
        if description is not None:
            inp["description"] = description
        if os_type is not None:
            inp["osType"] = os_type
        if propagation is not None:
            inp["propagation"] = propagation
        if label is not None:
            inp["label"] = label
        if exceptions_json:
            inp["exceptions"] = json.loads(exceptions_json)

        data = execute(mutation, {"input": inp})
        return json.dumps(data.get("updateNACSingleRule"), indent=2)

    @mcp.tool()
    def delete_nac_rules(
        rule_ids: list[str],
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Delete one or more NAC rules by their IDs.

        Args:
            rule_ids: List of numeric rule IDs to delete.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        mutation = """
        mutation DeleteNACRules($scope: ScopeSelectorInput, $ruleIds: [ID!]!) {
            deleteNACRules(scope: $scope, ruleIds: $ruleIds) {
                success id statusMessage
            }
        }
        """
        data = execute(mutation, {"scope": build_scope(scope_type, scope_ids), "ruleIds": rule_ids})
        return json.dumps(data.get("deleteNACRules"), indent=2)
