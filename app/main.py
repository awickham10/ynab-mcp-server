"""YNAB MCP Server entry point."""

from pathlib import Path

from cryptography.fernet import Fernet
from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.providers import FileSystemProvider
from fastmcp.utilities.logging import get_logger
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.apps import budget_summary_app, categorize_queue_app
from app.auth import YNABTokenVerifier
from app.config import config
from app.lifespan import http_client_lifespan

logger = get_logger(__name__)

SERVER_INSTRUCTIONS = (
    "Provides read/write access to YNAB budgets, accounts, transactions, "
    "categories, and payees. Use the read-only tools to inspect a budget "
    "and `update_transaction` to add memos or recategorize."
)


def _build_oauth_proxy_kwargs() -> dict:
    """Resolve persistence settings and warn loudly when running without them.

    On Linux defaults the JWT signing key is regenerated per process and the
    OAuth client storage lives in memory, which means every redeploy or new
    replica issues fresh keys and forgets every existing client. Setting
    JWT_SIGNING_KEY plus REDIS_URL + STORAGE_ENCRYPTION_KEY together fixes this.
    """
    kwargs: dict = {}

    if config.JWT_SIGNING_KEY is not None:
        kwargs["jwt_signing_key"] = config.JWT_SIGNING_KEY.get_secret_value()
    else:
        logger.warning(
            "JWT_SIGNING_KEY is not set. FastMCP will use an ephemeral signing key, "
            "so all client tokens become invalid every time the process restarts."
        )

    redis_url = config.REDIS_URL.get_secret_value() if config.REDIS_URL else None
    encryption_key = (
        config.STORAGE_ENCRYPTION_KEY.get_secret_value()
        if config.STORAGE_ENCRYPTION_KEY
        else None
    )

    if redis_url and not encryption_key:
        raise RuntimeError(
            "REDIS_URL is set but STORAGE_ENCRYPTION_KEY is not. Refusing to store "
            "OAuth tokens unencrypted. Generate a Fernet key with "
            "`python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` "
            "and set it as STORAGE_ENCRYPTION_KEY."
        )

    if redis_url and encryption_key:
        kwargs["client_storage"] = FernetEncryptionWrapper(
            key_value=RedisStore(url=redis_url),
            fernet=Fernet(encryption_key.encode()),
        )
    else:
        logger.warning(
            "REDIS_URL is not set. OAuth client registrations and upstream tokens "
            "will live in process memory only — clients will be disconnected on every "
            "restart and replicas can't share sessions."
        )

    return kwargs


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
        **_build_oauth_proxy_kwargs(),
    )

    fs_provider = FileSystemProvider(Path(__file__).parent / "components")

    server = FastMCP(
        config.server_name,
        instructions=SERVER_INSTRUCTIONS,
        auth=auth_provider,
        providers=[fs_provider, budget_summary_app, categorize_queue_app],
        lifespan=http_client_lifespan,
    )

    if config.YNAB_READ_ONLY:
        server.enable(tags={"readonly"}, only=True)

    @server.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    return server


mcp = create_mcp_server()
