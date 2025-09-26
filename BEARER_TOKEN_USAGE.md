# Bearer Token Authentication

This MCP server supports bearer token authentication, allowing clients to pass Google OAuth access tokens directly without going through the OAuth flow.

## Authentication Modes

### 1. Bearer Token Mode (`AUTH_MODE=bearer`)
- Uses only bearer tokens for authentication
- No OAuth flow required
- Tokens can be provided via environment variable or client requests

### 2. Hybrid Mode (`AUTH_MODE=hybrid`)
- Supports both OAuth and bearer token authentication
- Clients can choose either authentication method
- OAuth flow still available for interactive use

### 3. OAuth Mode (`AUTH_MODE=oauth`) - Default
- Traditional OAuth flow only
- No bearer token support

## How Clients Can Pass Bearer Tokens

### Method 1: Authorization Header (Recommended)
```bash
curl -H "Authorization: Bearer ya29.a0AfH6SMC..." \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_user_info", "arguments": {}}}' \
     http://localhost:8000/mcp
```

### Method 2: Query Parameter
```bash
curl -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_user_info", "arguments": {}}}' \
     "http://localhost:8000/mcp?access_token=ya29.a0AfH6SMC..."
```

### Method 3: Tool Parameter
```bash
curl -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "authenticate_with_bearer_token", "arguments": {"bearer_token": "ya29.a0AfH6SMC..."}}}' \
     http://localhost:8000/mcp
```

## Server Configuration

### Bearer Token Mode
```bash
export AUTH_MODE=bearer
export BEARER_TOKEN="ya29.a0AfH6SMC..."  # Optional fallback
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID="your-client-id"
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET="your-client-secret"
```

### Hybrid Mode
```bash
export AUTH_MODE=hybrid
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID="your-client-id"
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET="your-client-secret"
export FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL="http://localhost:8000"
export FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES="https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive"
```

## Testing Bearer Token Authentication

Use the provided test script:

```bash
# Test with Authorization header
python test_bearer_token.py --bearer-token "ya29.a0AfH6SMC..." --method header

# Test with query parameter
python test_bearer_token.py --bearer-token "ya29.a0AfH6SMC..." --method query

# Test with tool parameter
python test_bearer_token.py --bearer-token "ya29.a0AfH6SMC..." --method tool
```

## Getting Google OAuth Access Tokens

### Method 1: Google OAuth Playground
1. Go to [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
2. Select the required scopes:
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/drive`
3. Authorize and exchange for tokens
4. Use the access token

### Method 2: Programmatic OAuth
```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)
access_token = creds.token
```

### Method 3: Service Account (for server-to-server)
```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service-account.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
)
access_token = credentials.token
```

## Security Considerations

1. **Token Storage**: Store bearer tokens securely and never commit them to version control
2. **Token Expiration**: Google OAuth tokens expire (typically 1 hour). Implement token refresh logic
3. **HTTPS**: Always use HTTPS in production to protect tokens in transit
4. **Scope Validation**: Ensure tokens have the required scopes for your operations

## Error Handling

The server will return appropriate error messages for:
- Invalid or expired tokens
- Missing required scopes
- Network connectivity issues
- Malformed requests

Example error response:
```json
{
  "error": "Failed to authenticate with Google APIs using bearer token: 401 Unauthorized"
}
```

## Examples

### Python Client Example
```python
import requests

def call_mcp_tool(bearer_token, tool_name, arguments=None):
    url = "http://localhost:8000/mcp"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Usage
result = call_mcp_tool("ya29.a0AfH6SMC...", "get_sheet_data", {
    "spreadsheet_id": "your-spreadsheet-id",
    "sheet": "Sheet1"
})
```

### JavaScript Client Example
```javascript
async function callMCPTool(bearerToken, toolName, arguments = {}) {
    const response = await fetch('http://localhost:8000/mcp', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${bearerToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            id: 1,
            method: 'tools/call',
            params: {
                name: toolName,
                arguments: arguments
            }
        })
    });
    
    return await response.json();
}

// Usage
const result = await callMCPTool('ya29.a0AfH6SMC...', 'get_user_info');
```
