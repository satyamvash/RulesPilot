"""MCP tools for NAC CSV import and export."""
import json
from typing import Any
from mcp.server.fastmcp import FastMCP
from nac_mcp.client import execute
from nac_mcp.types import build_scope


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_nac_csv_sample_file() -> str:
        """Get a pre-signed download URL for the sample NAC rules CSV template."""
        query = """
        query {
            nacCsvExportRulesSampleFile { url expiresAt }
        }
        """
        data = execute(query)
        return json.dumps(data.get("nacCsvExportRulesSampleFile"), indent=2)

    @mcp.tool()
    def create_csv_upload_url(
        file_name: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
        content_type: str = "text/csv",
    ) -> str:
        """
        Create a pre-signed S3 URL for uploading a CSV rules file.
        Upload the file to the returned URL, then call import_csv_rules or validate_csv_rules
        with the returned fileOperationId.

        Args:
            file_name: Name of the CSV file to upload.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
            content_type: MIME type (default: text/csv).
        """
        mutation = """
        mutation CreateUploadUrl($input: NACFileUploadRequestInput!) {
            createNACFileUploadPreSignedUrl(input: $input) {
                fileOperationId presignedUrl expiresAt
            }
        }
        """
        inp = {
            "scope": build_scope(scope_type, scope_ids),
            "fileName": file_name,
            "contentType": content_type,
        }
        data = execute(mutation, {"input": inp})
        return json.dumps(data.get("createNACFileUploadPreSignedUrl"), indent=2)

    @mcp.tool()
    def validate_csv_rules(
        file_operation_id: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Trigger CSV validation (without importing). Use get_csv_validate_status to poll results.

        Args:
            file_operation_id: ID returned by create_csv_upload_url.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        mutation = """
        mutation ValidateCSV($input: NACCsvUploadedFileInput!) {
            validateNACCsvRules(input: $input) {
                status fileOperationId totalCount validCount invalidCount
            }
        }
        """
        inp = {"scope": build_scope(scope_type, scope_ids), "fileOperationId": file_operation_id}
        data = execute(mutation, {"input": inp})
        return json.dumps(data.get("validateNACCsvRules"), indent=2)

    @mcp.tool()
    def import_csv_rules(
        file_operation_id: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Trigger CSV import after the file has been uploaded. Use get_csv_import_status to poll results.

        Args:
            file_operation_id: ID returned by create_csv_upload_url.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        mutation = """
        mutation ImportCSV($input: NACCsvUploadedFileInput!) {
            importNACCsvRules(input: $input) {
                status fileOperationId totalCount importedCount failedCount
            }
        }
        """
        inp = {"scope": build_scope(scope_type, scope_ids), "fileOperationId": file_operation_id}
        data = execute(mutation, {"input": inp})
        return json.dumps(data.get("importNACCsvRules"), indent=2)

    @mcp.tool()
    def get_csv_import_status(
        file_operation_id: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Poll the status of a CSV import job.

        Args:
            file_operation_id: ID from create_csv_upload_url.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        query = """
        query ImportStatus($statusInput: NACCsvImportRulesStatusInput!) {
            nacCsvImportRulesStatus(statusInput: $statusInput) {
                status fileOperationId totalCount importedCount failedCount
            }
        }
        """
        inp = {"scope": build_scope(scope_type, scope_ids), "fileOperationId": file_operation_id}
        data = execute(query, {"statusInput": inp})
        return json.dumps(data.get("nacCsvImportRulesStatus"), indent=2)

    @mcp.tool()
    def get_csv_validate_status(
        file_operation_id: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Poll the status of a CSV validation job.

        Args:
            file_operation_id: ID from create_csv_upload_url.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        query = """
        query ValidateStatus($statusInput: NACCsvImportRulesStatusInput!) {
            nacCsvValidateRulesStatus(statusInput: $statusInput) {
                status fileOperationId totalCount validCount invalidCount
            }
        }
        """
        inp = {"scope": build_scope(scope_type, scope_ids), "fileOperationId": file_operation_id}
        data = execute(query, {"statusInput": inp})
        return json.dumps(data.get("nacCsvValidateRulesStatus"), indent=2)

    @mcp.tool()
    def export_csv_rules(
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
        include_parents: bool = False,
        filter_field: str | None = None,
        filter_value: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "ASC",
    ) -> str:
        """
        Start a CSV export job for NAC rules. Use get_csv_export_status to poll and get the download URL.

        Args:
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
            include_parents: Include rules from parent scopes.
            filter_field: Optional field to filter on.
            filter_value: Optional filter value (fulltext match).
            sort_by: Optional field to sort by.
            sort_order: ASC or DESC.
        """
        mutation = """
        mutation ExportCSV(
            $scope: ScopeSelectorInput,
            $filter: [CommonFilterInput],
            $sort: [CommonSortInput],
            $includeParents: Boolean
        ) {
            exportNACCsvRules(scope: $scope, filterInput: $filter, sortInput: $sort, includeParents: $includeParents) {
                status fileOperationId
            }
        }
        """
        variables: dict[str, Any] = {
            "scope": build_scope(scope_type, scope_ids),
            "includeParents": include_parents,
        }
        if filter_field and filter_value:
            variables["filter"] = [{"fieldId": filter_field, "match": {"value": filter_value}}]
        if sort_by:
            variables["sort"] = [{"by": sort_by, "order": sort_order}]

        data = execute(mutation, variables)
        return json.dumps(data.get("exportNACCsvRules"), indent=2)

    @mcp.tool()
    def get_csv_export_status(
        file_operation_id: str,
        scope_type: str | None = None,
        scope_ids: list[str] | None = None,
    ) -> str:
        """
        Poll the status of a CSV export job and get the download URL when complete.

        Args:
            file_operation_id: ID returned by export_csv_rules.
            scope_type: ACCOUNT, SITE, or GROUP. Defaults to NAC_DEFAULT_SCOPE_TYPE env var.
            scope_ids: List of scope IDs. Defaults to NAC_DEFAULT_SCOPE_IDS env var.
        """
        query = """
        query ExportStatus($statusInput: NACCsvExportRulesStatusInput!) {
            nacCsvExportRulesStatus(statusInput: $statusInput) {
                status fileOperationId url expiresAt
            }
        }
        """
        inp = {"scope": build_scope(scope_type, scope_ids), "fileOperationId": file_operation_id}
        data = execute(query, {"statusInput": inp})
        return json.dumps(data.get("nacCsvExportRulesStatus"), indent=2)
