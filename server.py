#!/usr/bin/env python3
"""YNAB MCP Server entry point."""

import os

from app.main import mcp

if __name__ == "__main__":
    # Mount the MCP endpoint at root. ChatGPT (and possibly other clients) sends
    # `resource=<base_url>` in the /authorize request rather than the full resource
    # URL declared in protected-resource metadata. Putting MCP at `/` makes the
    # advertised resource URL match the bare host so the proxy's resource-indicator
    # check in fastmcp 3.2.4 passes — otherwise the server raises invalid_target,
    # which the SDK then fails to serialize (see fastmcp issue: AuthorizationErrorResponse
    # rejects 'invalid_target' as a Literal value).
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        path="/",
    )
