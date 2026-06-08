# NAC MCP Server

MCP server wrapping the NAC App Control GraphQL API. Exposes tools for managing rules, settings, and CSV import/export.

## Setup

```bash
pip install -e .
cp .env.example .env
# Edit .env with your GraphQL URL and auth token
```

## Configuration

| Variable | Description |
|----------|-------------|
| `NAC_GRAPHQL_URL` | GraphQL endpoint URL |
| `NAC_AUTH_TOKEN` | Bearer token for authentication |

## Running

```bash
nac-mcp-server
```

Or via stdio (for Claude Desktop):
```bash
python -m nac_mcp.server
```

## Claude Desktop config

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "nac-app-control": {
      "command": "nac-mcp-server",
      "env": {
        "NAC_GRAPHQL_URL": "http://localhost:8080/graphql",
        "NAC_AUTH_TOKEN": "your-token"
      }
    }
  }
}
```

## Available Tools

### Rules
- `nac_health_check` — service liveness check
- `get_nac_rule` — fetch a single rule by ID
- `list_nac_rules` — paginated, filterable, sortable rule list
- `get_nac_rule_change_log` — audit history for a rule
- `validate_nac_rule` — field-level validation without persisting
- `create_or_update_nac_rule` — create (no id) or update (with id) a rule
- `delete_nac_rules` — bulk delete rules

### Settings
- `get_nac_settings` — get settings for a scope
- `update_nac_settings` — configure Application Control settings

### Metadata
- `get_nac_rule_column_metadata` — field metadata for filtering/sorting
- `get_nac_rule_filters_count` — faceted filter value counts

### CSV Import
- `get_nac_csv_sample_file` — download sample CSV template
- `create_csv_upload_url` — get S3 pre-signed upload URL
- `validate_csv_rules` — validate CSV without importing
- `import_csv_rules` — trigger import after upload
- `get_csv_validate_status` — poll validation progress
- `get_csv_import_status` — poll import progress

### CSV Export
- `export_csv_rules` — start export job
- `get_csv_export_status` — poll export status and get download URL
