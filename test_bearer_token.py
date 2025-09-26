#!/usr/bin/env python3
"""
Test script demonstrating how clients can pass bearer tokens to the MCP server.
"""

import requests
import json
import argparse

def test_bearer_token_auth(server_url, bearer_token, method="header"):
    """Test bearer token authentication with different methods"""
    
    base_url = server_url.rstrip('/')
    
    if method == "header":
        # Method 1: Authorization header
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
        
    elif method == "query":
        # Method 2: Query parameter
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_user_info",
                "arguments": {}
            }
        }
        
        response = requests.post(
            f"{base_url}/mcp?access_token={bearer_token}", 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
    elif method == "tool":
        # Method 3: Pass token as tool parameter
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "authenticate_with_bearer_token",
                "arguments": {
                    "bearer_token": bearer_token
                }
            }
        }
        
        response = requests.post(f"{base_url}/mcp", json=payload, headers={"Content-Type": "application/json"})
    
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return response

def main():
    parser = argparse.ArgumentParser(description="Test bearer token authentication")
    parser.add_argument("--server-url", default="http://localhost:8000", 
                       help="MCP server URL (default: http://localhost:8000)")
    parser.add_argument("--bearer-token", required=True,
                       help="Google OAuth 2.0 access token")
    parser.add_argument("--method", choices=["header", "query", "tool"], default="header",
                       help="Method to pass bearer token (default: header)")
    
    args = parser.parse_args()
    
    print(f"Testing bearer token authentication...")
    print(f"Server URL: {args.server_url}")
    print(f"Method: {args.method}")
    print(f"Token: {args.bearer_token[:10]}...{args.bearer_token[-10:]}")
    print("-" * 50)
    
    try:
        response = test_bearer_token_auth(args.server_url, args.bearer_token, args.method)
        
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
