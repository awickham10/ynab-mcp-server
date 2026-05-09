#!/usr/bin/env python3
"""
Test script to verify YNAB MCP Server can start up
"""

import asyncio
import sys
from app.main import mcp

async def test_server():
    """Test that the server can be instantiated and basic info retrieved"""
    try:
        print(f"✓ Server name: {mcp.name}")
        print(f"✓ Server has auth: {mcp.auth is not None}")
        
        # Test that tools are registered
        tools = await mcp.list_tools()
        print(f"✓ Registered tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description or 'No description'}")

        # Test that prompts are registered
        prompts = await mcp.list_prompts()
        print(f"✓ Registered prompts: {len(prompts)}")
        for prompt in prompts:
            print(f"  - {prompt.name}: {prompt.description or 'No description'}")
            
        print("\n✅ All tests passed! Server is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server())
    sys.exit(0 if success else 1)