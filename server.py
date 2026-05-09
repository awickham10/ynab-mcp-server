#!/usr/bin/env python3
"""YNAB MCP Server entry point."""

import os

from app.main import mcp

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
    )
