
# mcp-google-sheets

*MCP server to securely interact with Google Sheets via Google OAuth.* 📊

[![PyPI - Version](https://img.shields.io/pypi/v/mcp-google-sheets)](https://pypi.org/project/mcp-google-sheets/)
![GitHub License](https://img.shields.io/github/license/xing5/mcp-google-sheets)

---

## What is this?

`mcp-google-sheets` is an MCP server built on FastMCP. It exposes tools to read, write, format, share, and search Google Sheets and Drive, authenticated via Google OAuth. It is designed for MCP-compatible clients (e.g., Claude Desktop).

---

## Quick start

1) Install `uv` (if needed): see `https://astral.sh/uv`

2) Set environment variables for Google OAuth (required):
        ```bash
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID="<your_client_id>"
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET="<your_client_secret>"
export FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL="http://localhost:8000"   # public URL of this server
export FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive"
# Optional: scope Drive to a folder for create/list
export DRIVE_FOLDER_ID="<drive_folder_id>"
```

3) Run the server:
        ```bash
        uvx mcp-google-sheets@latest
        ```

The server defaults to HTTP transport on `0.0.0.0:8000` and prints the OAuth callback URL.

---

## Tools exposed

- `get_user_info()`: Return authenticated Google user info from token claims.
- `get_sheet_data(spreadsheet_id, sheet, range?, include_grid_data?)`: Read values or full grid data.
- `get_sheet_formulas(spreadsheet_id, sheet, range?)`: Read formulas.
- `update_cells(spreadsheet_id, sheet, range, data)`: Write values.
- `batch_update_cells(spreadsheet_id, sheet, ranges{range->values})`: Write multiple ranges.
- `add_rows(spreadsheet_id, sheet, count, start_row?)`: Insert rows.
- `add_columns(spreadsheet_id, sheet, count, start_column?)`: Insert columns.
- `list_sheets(spreadsheet_id)`: List sheet names.
- `copy_sheet(src_spreadsheet, src_sheet, dst_spreadsheet, dst_sheet)`: Copy/rename sheet across files.
- `rename_sheet(spreadsheet, sheet, new_name)`: Rename sheet.
- `get_multiple_sheet_data(queries[])`: Fetch multiple ranges across files.
- `get_multiple_spreadsheet_summary(spreadsheet_ids[], rows_to_fetch=5)`: Titles, sheet names, headers, first rows.
- `get_spreadsheet_info(spreadsheet_id)`: Basic spreadsheet info (JSON string).
- `create_spreadsheet(title)`: Create spreadsheet (in `DRIVE_FOLDER_ID` if set).
- `create_sheet(spreadsheet_id, title)`: Add tab.
- `list_spreadsheets()`: List spreadsheets (folder-scoped if `DRIVE_FOLDER_ID`).
- `share_spreadsheet(spreadsheet_id, recipients[], send_notification?)`: Assign Drive permissions.
- `search(query, limit=10)`: Search titles and cell contents across accessible spreadsheets.
- `format_cells(spreadsheet_id, sheet, range, formatting{})`: Apply formatting, borders, wrap, merge.
- `get_formatting_presets()`: Common formatting presets.
- `fetch(id)`: Resource fetcher:
  - `spreadsheet://{spreadsheet_id}/info`
  - `spreadsheet://{spreadsheet_id}/{sheet}`
  - `spreadsheet://{spreadsheet_id}/{sheet}/{range}`

Custom route:
- `GET /clear_oauth_cache`: Clear cached OAuth tokens (debugging).

---

## Minimal client config (Claude Desktop)

```json
{
  "mcpServers": {
    "google-sheets": {
      "command": "uvx",
      "args": ["mcp-google-sheets@latest"],
      "env": {
        "FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID": "<client_id>",
        "FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET": "<client_secret>",
        "FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL": "http://localhost:8000",
        "FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES": "openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive",
        "DRIVE_FOLDER_ID": "<optional_folder_id>"
      }
    }
  }
}
```

---

## ☁️ Google Cloud Platform Setup

This setup is **required** before running the server.

1.  **Create/Select a GCP Project:** Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Enable APIs:** Navigate to "APIs & Services" -> "Library". Search for and enable:
    *   `Google Sheets API`
    *   `Google Drive API`
3.  **Create OAuth 2.0 Client ID:**
    *   Go to **APIs & Services → OAuth consent screen**
    *   Choose "External" for testing or "Internal" for G Suite organizations
    *   Go to **APIs & Services → Credentials**
    *   Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
    *   Configure your OAuth client:
      - **Application type**: Web application
      - **Name**: Choose a descriptive name (e.g., "FastMCP Google Sheets Server")
      - **Authorized JavaScript origins**: Add your server's base URL (e.g., `http://localhost:8000`)
      - **Authorized redirect URIs**: Add these URLs:
        - Your server URL + `/auth/callback` (e.g., `http://localhost:8000/auth/callback`)
        - For Cursor MCP client: `cursor://anysphere.cursor-retrieval/oauth/user-mcp-google-sheets/callback`
        - For other MCP clients, check their documentation for the required redirect URI

## Troubleshooting

**Common OAuth Issues:**
- `redirect_uri_mismatch`: The redirect URI in the request doesn't match the configured URIs
- `invalid_client`: Client ID or secret is incorrect
- `access_denied`: User denied permission or scope issues

**Security Notes:**
- Never commit OAuth credentials to version control
- Use environment variables or a secrets manager in production
- For production deployments, use HTTPS URLs

---

## License

MIT — see `LICENSE`.
