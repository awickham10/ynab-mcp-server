#!/usr/bin/env python3
"""
YNAB MCP Server Runner

Simple runner script for the YNAB MCP server to work around FastMCP module loading issues.
"""

from app.main import mcp

if __name__ == "__main__":
    # This allows FastMCP to find the server instance
    pass