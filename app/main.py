"""YNAB MCP Server entry point."""

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.providers import FileSystemProvider

from app.auth import YNABTokenVerifier
from app.config import config
from app.lifespan import http_client_lifespan

SERVER_INSTRUCTIONS = (
    "Provides read/write access to YNAB budgets, accounts, transactions, "
    "categories, and payees. Use the read-only tools to inspect a budget "
    "and `update_transaction` to add memos or recategorize."
)


def create_mcp_server() -> FastMCP:
    """Factory function to create and configure the MCP server."""

    token_verifier = YNABTokenVerifier()

    auth_provider = OAuthProxy(
        upstream_authorization_endpoint="https://app.ynab.com/oauth/authorize",
        upstream_token_endpoint="https://app.ynab.com/oauth/token",
        upstream_client_id=config.YNAB_CLIENT_ID,
        upstream_client_secret=config.YNAB_CLIENT_SECRET.get_secret_value(),
        token_verifier=token_verifier,
        base_url=config.YNAB_BASE_URL,
        redirect_path="/oauth/callback",
        issuer_url=config.YNAB_BASE_URL,
    )

    fs_provider = FileSystemProvider(Path(__file__).parent / "components")

    server = FastMCP(
        config.server_name,
        instructions=SERVER_INSTRUCTIONS,
        auth=auth_provider,
        providers=[fs_provider],
        lifespan=http_client_lifespan,
    )

    if config.YNAB_READ_ONLY:
        server.enable(tags={"readonly"}, only=True)

    return server


mcp = create_mcp_server()
