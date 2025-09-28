"""YNAB OAuth provider for FastMCP.

This module provides a complete YNAB integration that's ready to use with
just the client ID, client secret, and base URL.

Example:
    ```python
    from fastmcp import FastMCP
    from .auth.ynab import YNABProvider

    # Simple YNAB OAuth protection
    auth = YNABProvider(
        client_id="your-ynab-client-id",
        client_secret="your-ynab-client-secret",
        base_url="http://localhost:8000",
        read_only=True,  # Optional: request read-only access
    )

    mcp = FastMCP("My Protected Server", auth=auth)
    ```
"""

import httpx
import time
from pydantic import AnyHttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastmcp.server.auth import OAuthProxy, TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.utilities.auth import parse_scopes
from fastmcp.utilities.logging import get_logger
from fastmcp.utilities.storage import KVStorage
from fastmcp.utilities.types import NotSet, NotSetT

logger = get_logger(__name__)

print("[DEBUG] ynab.py module loaded - importing YNABProvider")


class YNABTokenVerifier(TokenVerifier):
    """Custom token verifier for YNAB OAuth tokens."""

    def __init__(self, *, timeout_seconds: int = 10):
        """Initialize the YNAB token verifier.
        
        Args:
            timeout_seconds: HTTP request timeout
        """
        super().__init__()
        self.timeout_seconds = timeout_seconds
        print(f"[DEBUG] YNABTokenVerifier initialized with timeout {timeout_seconds}s")
        logger.error("YNABTokenVerifier initialized - this should appear!")  # Use ERROR level to ensure it shows

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a token - could be our own issued token or a YNAB token.
        
        Args:
            token: The access token to verify
            
        Returns:
            AccessToken: Token information including user data, or None if invalid
        """
        print(f"[DEBUG] YNABTokenVerifier.verify_token called with token: {token[:20]}...")
        logger.error(f"YNABTokenVerifier.verify_token called with token: {token[:20]}... (length: {len(token)})")
        
        # First, try to verify as our own OAuth proxy token
        # OAuth proxy tokens are typically longer and contain different structure
        try:
            # If this is a token issued by our OAuth proxy, it might be a JWT or similar
            # Let's first try the parent class verification
            if hasattr(super(), 'verify_token'):
                logger.info("Trying parent class token verification first...")
                result = await super().verify_token(token)
                if result is not None:
                    logger.info("Token verified by parent class successfully")
                    return result
                logger.info("Parent class verification failed, trying YNAB API...")
        except Exception as e:
            logger.info(f"Parent class verification error: {e}")
        
        try:
            # Make a test API call to YNAB's /user endpoint to verify the token
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    "https://api.ynab.com/v1/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": "FastMCP-YNAB-OAuth",
                    },
                )
                
                if response.status_code != 200:
                    logger.info(
                        "YNAB token verification failed: %d - %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return None
                
                user_data = response.json()
                user_info = user_data.get("data", {}).get("user", {})
                
                logger.info(f"YNAB token verified successfully for user: {user_info.get('id', 'unknown')}")
                
                # YNAB tokens don't have explicit expiration, but typically last 2 hours
                # Set a conservative 1.5 hour expiration
                expires_at = int(time.time() + (90 * 60))  # 90 minutes from now
                
                # Return AccessToken object in the expected format
                return AccessToken(
                    token=token,
                    client_id="ynab-client",  # YNAB doesn't provide client_id in response
                    scopes=["read-only"],     # YNAB uses read-only scope
                    expires_at=expires_at,
                    claims={
                        "sub": user_info.get("id", "unknown"),
                        "email": user_info.get("email"),
                        "ynab_user_data": user_info,
                    }
                )
                
        except Exception as e:
            logger.info("YNAB token verification error: %s", e)
            return None


class YNABProviderSettings(BaseSettings):
    """Settings for YNAB OAuth provider."""

    model_config = SettingsConfigDict(
        env_prefix="FASTMCP_SERVER_AUTH_YNAB_",
        env_file=".env",
        extra="ignore",
    )

    client_id: str | None = None
    client_secret: SecretStr | None = None
    base_url: AnyHttpUrl | None = None
    redirect_path: str | None = None
    read_only: bool | None = None
    allowed_client_redirect_uris: list[str] | None = None


class YNABProvider(OAuthProxy):
    """A YNAB OAuth provider implementation for FastMCP.

    This provider is a complete YNAB integration that's ready to use with
    just the client ID, client secret, and base URL.

    Example:
        ```python
        from fastmcp import FastMCP
        from .auth.ynab import YNABProvider

        # Simple YNAB OAuth protection
        auth = YNABProvider(
            client_id="your-ynab-client-id",
            client_secret="your-ynab-client-secret",
            base_url="http://localhost:8000",
            read_only=True,  # Optional: request read-only access
        )

        mcp = FastMCP("My Protected Server", auth=auth)
        ```
    """

    def __init__(
        self,
        *,
        client_id: str | NotSetT = NotSet,
        client_secret: str | NotSetT = NotSet,
        base_url: AnyHttpUrl | str | NotSetT = NotSet,
        redirect_path: str | NotSetT = NotSet,
        read_only: bool | NotSetT = NotSet,
        allowed_client_redirect_uris: list[str] | NotSetT = NotSet,
        client_storage: KVStorage | None = None,
    ) -> None:
        """Initialize YNAB OAuth provider.

        Args:
            client_id: YNAB OAuth application client id
            client_secret: YNAB OAuth application client secret
            base_url: Public URL of your FastMCP server (for OAuth callbacks)
            read_only: Whether to request read-only access (defaults to False)
            redirect_path: Redirect path configured in YNAB application
            allowed_client_redirect_uris: List of allowed redirect URI patterns for MCP clients.
                If None (default), all URIs are allowed. If empty list, no URIs are allowed.
            client_storage: Storage implementation for OAuth client registrations.
                Defaults to file-based storage if not specified.
        """
        settings = YNABProviderSettings.model_validate(
            {
                k: v
                for k, v in {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "base_url": base_url,
                    "redirect_path": redirect_path,
                    "read_only": read_only,
                    "allowed_client_redirect_uris": allowed_client_redirect_uris,
                }.items()
                if v is not NotSet
            }
        )

        if not settings.client_id:
            raise ValueError(
                "client_id is required - set via parameter or FASTMCP_SERVER_AUTH_YNAB_CLIENT_ID"
            )

        if not settings.client_secret:
            raise ValueError(
                "client_secret is required - set via parameter or FASTMCP_SERVER_AUTH_YNAB_CLIENT_SECRET"
            )

        if not settings.base_url:
            raise ValueError(
                "base_url is required - set via parameter or FASTMCP_SERVER_AUTH_YNAB_BASE_URL"
            )

        # YNAB OAuth endpoints
        authorization_endpoint = "https://app.ynab.com/oauth/authorize"
        token_endpoint = "https://app.ynab.com/oauth/token"
        
        # Build extra authorize params for read-only scope if requested
        extra_authorize_params = {}
        if settings.read_only:
            extra_authorize_params["scope"] = "read-only"

        # Use custom YNAB TokenVerifier that validates tokens with YNAB API
        token_verifier = YNABTokenVerifier(timeout_seconds=10)

        init_kwargs = {
            "upstream_authorization_endpoint": authorization_endpoint,
            "upstream_token_endpoint": token_endpoint,
            "upstream_client_id": settings.client_id,
            "upstream_client_secret": settings.client_secret.get_secret_value(),
            "token_verifier": token_verifier,
            "base_url": settings.base_url,
            "redirect_path": settings.redirect_path,
            "issuer_url": settings.base_url,  # We act as the issuer for client registration
            "allowed_client_redirect_uris": settings.allowed_client_redirect_uris,
            "client_storage": client_storage,
            "extra_authorize_params": extra_authorize_params if extra_authorize_params else None,
        }

        super().__init__(**init_kwargs)

        print(f"[DEBUG] YNABProvider initialized successfully")
        logger.info(
            "Initialized YNAB OAuth provider for client %s with read_only=%s",
            settings.client_id,
            settings.read_only or False,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Load and verify access token. This might be called instead of verify_token."""
        print(f"[DEBUG] YNABProvider.load_access_token called with token: {token[:20]}...")
        logger.error(f"YNABProvider.load_access_token called with token: {token[:20]}...")
        return await self._token_verifier.verify_token(token)

    def get_routes(self, mcp_path: str | None = None, mcp_endpoint = None):
        """Override to add custom route handling for MCP Inspector compatibility."""
        routes = super().get_routes(mcp_path, mcp_endpoint)
        
        # Add alias for MCP Inspector's expected endpoint format
        if mcp_path:
            from starlette.routing import Route
            from starlette.responses import RedirectResponse
            
            # Add redirect from /mcp suffixed well-known endpoint to correct endpoint
            async def redirect_well_known(request):
                return RedirectResponse(
                    url="/.well-known/oauth-protected-resource",
                    status_code=302
                )
            
            routes.append(
                Route(
                    "/.well-known/oauth-protected-resource/mcp",
                    endpoint=redirect_well_known,
                    methods=["GET", "OPTIONS"]
                )
            )
            
        logger.debug(f"Generated {len(routes)} routes for YNAB provider")
        return routes
    
    async def authenticate(self, request):
        """Override authenticate to add debugging."""
        print(f"[DEBUG] YNABProvider.authenticate called")
        logger.error("YNABProvider.authenticate called")
        return await super().authenticate(request)
