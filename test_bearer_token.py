#!/usr/bin/env python3
"""
Test script demonstrating how clients can pass bearer tokens to the MCP server via Authorization header.
"""

import requests
import json
import argparse

def test_bearer_token_auth(server_url, bearer_token):
    """Test bearer token authentication via Authorization header"""
    
    base_url = server_url.rstrip('/')
    
    # Authorization header method
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    # Test with a simple tool call
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_user_info",
            "arguments": {}
        }
    }
    
    response = requests.post(f"{base_url}/mcp", json=payload, headers=headers)
    return response

def main():
    parser = argparse.ArgumentParser(description="Test bearer token authentication via Authorization header")
    parser.add_argument("--server-url", default="http://localhost:8000", 
                       help="MCP server URL (default: http://localhost:8000)")
    parser.add_argument("--bearer-token", required=True,
                       help="Google OAuth 2.0 access token")
    
    args = parser.parse_args()
    
    print(f"Testing bearer token authentication via Authorization header...")
    print(f"Server URL: {args.server_url}")
    print(f"Token: {args.bearer_token[:10]}...{args.bearer_token[-10:]}")
    print("-" * 50)
    
    try:
        response = test_bearer_token_auth(args.server_url, args.bearer_token)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
