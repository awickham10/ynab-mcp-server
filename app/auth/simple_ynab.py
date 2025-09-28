"""
Simple YNAB Token Verifier for FastMCP

This is a simpler approach that uses direct token verification instead of OAuth proxy.
Users will need to provide their YNAB personal access token directly.
"""

import httpx
import time
from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)

class SimpleYNABVerifier(TokenVerifier):
    """Simple YNAB token verifier that validates tokens against YNAB API."""
    
    def __init__(self):
        super().__init__()
        print("[DEBUG] SimpleYNABVerifier initialized")
        logger.error("SimpleYNABVerifier initialized")
    
    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify YNAB token by calling YNAB API directly."""
        print(f"[DEBUG] SimpleYNABVerifier.verify_token called with: {token[:20]}...")
        logger.error(f"SimpleYNABVerifier.verify_token called with: {token[:20]}...")
        
        # Temporary test token for development
        if token == "test-token-123":
            logger.error("Using test token - bypassing YNAB API")
            return AccessToken(
                token=token,
                client_id="ynab-test",
                scopes=["read-only"],
                expires_at=int(time.time() + (90 * 60)),
                claims={
                    "sub": "test-user-123",
                    "email": "test@example.com",
                    "ynab_user_data": {"id": "test-user-123"},
                }
            )
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.ynab.com/v1/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": "FastMCP-Simple-YNAB",
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"YNAB token verification failed: {response.status_code}")
                    return None
                
                user_data = response.json()
                user_info = user_data.get("data", {}).get("user", {})
                
                logger.error(f"YNAB token verified for user: {user_info.get('id', 'unknown')}")
                
                return AccessToken(
                    token=token,
                    client_id="ynab-direct",
                    scopes=["read-only"],
                    expires_at=int(time.time() + (90 * 60)),  # 90 minutes
                    claims={
                        "sub": user_info.get("id", "unknown"),
                        "email": user_info.get("email"),
                        "ynab_user_data": user_info,
                    }
                )
                
        except Exception as e:
            logger.error(f"YNAB token verification error: {e}")
            return None