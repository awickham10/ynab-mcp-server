"""
Authentication components for YNAB MCP Server
"""

from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.utilities.logging import get_logger
import httpx
import time

logger = get_logger(__name__)


class YNABTokenVerifier(TokenVerifier):
    """Token verifier for YNAB access tokens."""
    
    def __init__(self):
        # Don't require specific scopes, let YNAB handle scope validation
        super().__init__(required_scopes=[])
    
    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify token with YNAB API."""
        logger.debug(f"YNABTokenVerifier.verify_token called with token: {token[:20]}...")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.ynab.com/v1/user",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                logger.debug(f"YNAB API response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.debug(f"YNAB API error response: {response.text}")
                    return None
                
                user_data = response.json()
                user_info = user_data.get("data", {}).get("user", {})
                
                logger.debug(f"YNAB user verified: {user_info.get('id', 'unknown')}")
                
                # YNAB tokens typically last 2 hours
                expires_at = int(time.time() + (2 * 60 * 60))
                
                return AccessToken(
                    token=token,
                    client_id="ynab-client",
                    scopes=["read-only"],
                    expires_at=expires_at,
                    claims={
                        "sub": user_info.get("id", "unknown"),
                        "email": user_info.get("email"),
                        "ynab_user_data": user_info,
                    }
                )
        except Exception as e:
            logger.debug(f"Token verification error: {e}")
            return None