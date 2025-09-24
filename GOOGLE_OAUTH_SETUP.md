# Google OAuth Setup for FastMCP Google Sheets Server

This guide explains how to set up Google OAuth authentication using FastMCP's built-in Google OAuth provider. **Google OAuth is now the only supported authentication method** for this server.

## Prerequisites

1. A **Google Cloud Account** with access to create OAuth 2.0 Client IDs
2. Your FastMCP server's URL (can be localhost for development, e.g., `http://localhost:8000`)

## Step 1: Create a Google OAuth 2.0 Client ID

1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Go to **APIs & Services → OAuth consent screen**
   - Choose "External" for testing or "Internal" for G Suite organizations
4. Go to **APIs & Services → Credentials**
5. Click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
6. Configure your OAuth client:
   - **Application type**: Web application
   - **Name**: Choose a descriptive name (e.g., "FastMCP Google Sheets Server")
   - **Authorized JavaScript origins**: Add your server's base URL (e.g., `http://localhost:8000`)
   - **Authorized redirect URIs**: Add these URLs:
     - Your server URL + `/auth/callback` (e.g., `http://localhost:8000/auth/callback`)
     - For Cursor MCP client: `cursor://anysphere.cursor-retrieval/oauth/user-mcp-google-sheets/callback`
     - For other MCP clients, check their documentation for the required redirect URI

## Step 2: Configure Environment Variables

Set the following environment variables:

```bash
# Required: Your Google OAuth 2.0 Client ID
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID="123456789.apps.googleusercontent.com"

# Required: Your Google OAuth 2.0 Client Secret
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET="GOCSPX-abc123..."

# Optional: Public URL of your FastMCP server (default: http://localhost:8000)
export FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL="http://localhost:8000"

# Optional: Required Google scopes (default includes Sheets and Drive access)
export FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive"

# Server configuration
export MCP_TRANSPORT="http"
export MCP_HOST="0.0.0.0"
export MCP_PORT="8000"
```

## Step 3: Run the Server

```bash
python src/mcp_google_sheets/server.py
```

The server will start with Google OAuth authentication enabled. You should see:

```
✅ FastMCP Google OAuth authentication enabled
   Base URL: http://localhost:8000
   Scopes: openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive
OAuth callback URL: http://localhost:8000/auth/callback
```

## Step 4: Test with a Client

Create a test client that authenticates with your Google-protected server:

```python
from fastmcp import Client
import asyncio

async def main():
    # The client will automatically handle Google OAuth
    async with Client("http://localhost:8000/mcp", auth="oauth") as client:
        # First-time connection will open Google login in your browser
        print("✓ Authenticated with Google!")
        
        # Test the protected tool
        result = await client.call_tool("get_user_info")
        # The result may be wrapped in 'content' or 'structured_content'
        user_info = (
            result.get("content")
            or result.get("structured_content")
            or result
        )
        print(f"Google user: {user_info['email']}")
        print(f"Name: {user_info['name']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Authentication Requirements

**Google OAuth is required** - the server will not start without proper OAuth configuration. No fallback authentication methods are supported.

## Environment Variables Reference

### Google OAuth Configuration
- `FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID`: Your Google OAuth 2.0 Client ID
- `FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET`: Your Google OAuth 2.0 Client Secret
- `FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL`: Public URL of your FastMCP server for OAuth callbacks
- `FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES`: Required Google scopes (comma-separated)
- `FASTMCP_SERVER_AUTH_GOOGLE_REDIRECT_PATH`: Redirect path for OAuth callbacks (default: `/auth/callback`)

### Server Configuration
- `MCP_TRANSPORT`: Transport protocol ('http', 'stdio', or 'sse', default: 'http')
- `MCP_HOST`: Host to bind to (default: '0.0.0.0')
- `MCP_PORT`: Port to listen on (default: 8000)
- `FASTMCP_LOG_LEVEL`: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

### Optional Configuration
- `DRIVE_FOLDER_ID`: Google Drive folder ID for organizing spreadsheets

## Troubleshooting

### OAuth Redirect URI Issues

If you see a `302 Found` response in your server logs but authentication fails, check that your Google OAuth Client has the correct redirect URIs configured:

**For Cursor MCP Client:**
- Add: `cursor://anysphere.cursor-retrieval/oauth/user-mcp-google-sheets/callback`

**For General Testing:**
- Add: `http://localhost:8000/auth/callback`

**Common Error Messages:**
- `redirect_uri_mismatch`: The redirect URI in the request doesn't match the configured URIs
- `invalid_client`: Client ID or secret is incorrect
- `access_denied`: User denied permission or scope issues

### Server Logs

Monitor your server logs for OAuth flow messages:
```
INFO: 127.0.0.1:xxxxx - "GET /authorize?response_type=code&client_id=..." 302 Found
```

This indicates the OAuth flow is working correctly.

## Security Notes

- Never commit OAuth credentials to version control
- Use environment variables or a secrets manager in production
- For production deployments, use HTTPS URLs
- The redirect URI must match exactly between your Google OAuth Client settings and the client's expected URI
