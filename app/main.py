"""
YNAB MCP Server - Refactored Enterprise Architecture

This server provides Model Context Protocol (MCP) access to YNAB (You Need A Budget) 
data through secure OAuth authentication with enterprise-grade architecture.
"""

from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy, TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.utilities.logging import get_logger
import httpx
import time

from app.config import config
from app.tools import register_tools
from app.prompts import register_prompts

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


def _log_registered_resources(mcp_server: FastMCP) -> None:
    """Log all registered tools and prompts for debugging and visibility"""
    
    logger.info("_log_registered_resources called!")  # Debug log
    
    # Get registered tools - try different possible attribute names
    try:
        # First, let's see what attributes the server has
        server_attrs = [attr for attr in dir(mcp_server) if not attr.startswith('__')]
        logger.info(f"FastMCP server attributes: {server_attrs}")
        
        # Try different ways to access tools and prompts
        tools = {}
        prompts = {}
        
        # Try to get tools using FastMCP methods
        if hasattr(mcp_server, 'get_tools'):
            try:
                tools_list = mcp_server.get_tools()
                tools = {tool.name: tool for tool in tools_list}
                logger.info(f"Found {len(tools)} tools using get_tools() method")
            except Exception as e:
                logger.debug(f"Error calling get_tools(): {e}")
        
        # Try to get prompts using FastMCP methods  
        if hasattr(mcp_server, 'get_prompts'):
            try:
                prompts_list = mcp_server.get_prompts()
                prompts = {prompt.name: prompt for prompt in prompts_list}
                logger.info(f"Found {len(prompts)} prompts using get_prompts() method")
            except Exception as e:
                logger.debug(f"Error calling get_prompts(): {e}")
        
        # If the above methods don't work, try accessing the managers directly
        if not tools and hasattr(mcp_server, '_tool_manager'):
            try:
                tool_manager = mcp_server._tool_manager
                if hasattr(tool_manager, 'tools'):
                    tools = tool_manager.tools
                    logger.info(f"Found {len(tools)} tools from _tool_manager.tools")
                elif hasattr(tool_manager, '_tools'):
                    tools = tool_manager._tools
                    logger.info(f"Found {len(tools)} tools from _tool_manager._tools")
            except Exception as e:
                logger.debug(f"Error accessing _tool_manager: {e}")
        
        if not prompts and hasattr(mcp_server, '_prompt_manager'):
            try:
                prompt_manager = mcp_server._prompt_manager
                if hasattr(prompt_manager, 'prompts'):
                    prompts = prompt_manager.prompts
                    logger.info(f"Found {len(prompts)} prompts from _prompt_manager.prompts")
                elif hasattr(prompt_manager, '_prompts'):
                    prompts = prompt_manager._prompts
                    logger.info(f"Found {len(prompts)} prompts from _prompt_manager._prompts")
            except Exception as e:
                logger.debug(f"Error accessing _prompt_manager: {e}")
        
        logger.info("=" * 60)
        logger.info("YNAB MCP SERVER STARTUP - REGISTERED RESOURCES")
        logger.info("=" * 60)
        
        # Log tools
        if tools:
            logger.info(f"� REGISTERED TOOLS ({len(tools)}):")
            for tool_name, tool_func in tools.items():
                # Try to get the docstring for description
                doc = getattr(tool_func, '__doc__', 'No description available')
                if doc:
                    # Get just the first line of the docstring
                    description = doc.strip().split('\n')[0]
                else:
                    description = "No description available"
                logger.info(f"  • {tool_name}: {description}")
        else:
            logger.warning("  ⚠️  No tools found")
        
        logger.info("")
        
        # Log prompts
        if prompts:
            logger.info(f"💬 REGISTERED PROMPTS ({len(prompts)}):")
            for prompt_name, prompt_func in prompts.items():
                # Try to get the docstring for description
                doc = getattr(prompt_func, '__doc__', 'No description available')
                if doc:
                    # Get just the first line of the docstring
                    description = doc.strip().split('\n')[0]
                else:
                    description = "No description available"
                logger.info(f"  • {prompt_name}: {description}")
        else:
            logger.warning("  ⚠️  No prompts found")
        
        logger.info("=" * 60)
        logger.info(f"✅ SERVER READY - {len(tools)} tools, {len(prompts)} prompts available")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error logging registered resources: {e}")
        logger.info("Server started but couldn't enumerate registered tools/prompts")


def create_mcp_server() -> FastMCP:
    """Factory function to create and configure the MCP server"""
    
    # Create YNAB token verifier
    token_verifier = YNABTokenVerifier()
    
    # Create standard OAuth proxy for YNAB
    auth_provider = OAuthProxy(
        upstream_authorization_endpoint="https://app.ynab.com/oauth/authorize",
        upstream_token_endpoint="https://app.ynab.com/oauth/token",
        upstream_client_id=config.YNAB_CLIENT_ID,
        upstream_client_secret=config.YNAB_CLIENT_SECRET.get_secret_value(),
        token_verifier=token_verifier,
        base_url=config.YNAB_BASE_URL,
        redirect_path="/oauth/callback",  # YNAB OAuth callback path
        issuer_url=config.YNAB_BASE_URL,  # Our server acts as the OAuth issuer
        # Remove read-only scope temporarily to test
        # extra_authorize_params={"scope": "read-only"} if config.YNAB_READ_ONLY else None,
    )
    
    # Create server with OAuth authentication
    mcp_server = FastMCP(config.server_name, auth=auth_provider)
    
    # Register all tools and prompts
    logger.info("Registering YNAB MCP tools and prompts...")
    register_tools(mcp_server)
    register_prompts(mcp_server)
    
    # Log all registered tools and prompts
    logger.info("About to log registered resources...")
    _log_registered_resources(mcp_server)
    logger.info("Finished logging registered resources.")
    
    return mcp_server


# Create the MCP server instance
mcp = create_mcp_server()