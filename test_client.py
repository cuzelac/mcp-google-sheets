from fastmcp import Client
import asyncio
import argparse
import json

async def list_tools(client):
    """List all available tools from the MCP server."""
    try:
        # Get the server info which includes available tools
        tools = await client.list_tools()
        print("Available tools:")
        print("=" * 50)
        
        for tool in tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description}")
            
            if tool.inputSchema and tool.inputSchema.get('properties'):
                print("Parameters:")
                for param_name, param_info in tool.inputSchema['properties'].items():
                    param_type = param_info.get('type', 'unknown')
                    param_desc = param_info.get('description', 'No description')
                    required = param_name in tool.inputSchema.get('required', [])
                    required_str = " (required)" if required else " (optional)"
                    print(f"  - {param_name}: {param_type}{required_str}")
                    print(f"    {param_desc}")
            else:
                print("Parameters: None")
                
    except Exception as e:
        print(f"Error listing tools: {e}")

async def call_tool_by_name(client, tool_name, args_dict=None):
    """Call a specific tool with given arguments."""
    try:
        if args_dict:
            result = await client.call_tool(tool_name, args_dict)
        else:
            result = await client.call_tool(tool_name)
        
        if result.is_error:
            print(f"Error calling tool '{tool_name}': {result.content}")
            return
            
        print(f"Result from '{tool_name}':")
        print("=" * 50)
        
        if result.structured_content:
            print(json.dumps(result.structured_content, indent=2))
        else:
            print(result.content)
            
    except Exception as e:
        print(f"Error calling tool '{tool_name}': {e}")

async def main():
    parser = argparse.ArgumentParser(description="Test MCP Google Sheets client")
    parser.add_argument("--list-tools", action="store_true", 
                       help="List all available tools from the MCP server")
    parser.add_argument("--call-tool", type=str, 
                       help="Call a specific tool by name")
    parser.add_argument("--args", type=str, 
                       help="JSON string of arguments to pass to the tool")
    parser.add_argument("--server-url", default="http://localhost:8000/mcp",
                       help="MCP server URL (default: http://localhost:8000/mcp)")
    
    args = parser.parse_args()
    
    # The client will automatically handle Google OAuth
    async with Client(args.server_url, auth="oauth") as client:
        # First-time connection will open Google login in your browser
        print("✓ Authenticated with Google!")
        
        if args.list_tools:
            await list_tools(client)
        elif args.call_tool:
            # Parse arguments if provided
            tool_args = None
            if args.args:
                try:
                    tool_args = json.loads(args.args)
                except json.JSONDecodeError as e:
                    print(f"Error parsing arguments JSON: {e}")
                    return
            
            await call_tool_by_name(client, args.call_tool, tool_args)
        else:
            # Default behavior - test the get_user_info tool
            print("No specific action requested. Testing get_user_info tool:")
            await call_tool_by_name(client, "get_user_info")

if __name__ == "__main__":
    asyncio.run(main())
