"""
YNAB MCP Server - Refactored Enterprise Architecture

This server provides Model Context Protocol (MCP) access to YNAB (You Need A Budget) 
data through secure OAuth authentication with enterprise-grade architecture.
"""

from fastmcp import FastMCP
from fastmcp.server.auth import OAuthProxy
from fastmcp.utilities.logging import get_logger

from app.auth import YNABTokenVerifier
from app.config import config
from app.tools import register_tools
from app.prompts import register_prompts

logger = get_logger(__name__)


def _log_registered_resources(mcp_server: FastMCP) -> None:
    """Log all registered tools and prompts for debugging and visibility"""
    
    logger.info("_log_registered_resources called!")  # Debug log
    
    # Get registered tools - access managers directly to avoid async calls
    try:
        tools = {}
        prompts = {}
        
        # Access tool manager directly
        if hasattr(mcp_server, '_tool_manager'):
            try:
                tool_manager = mcp_server._tool_manager
                if hasattr(tool_manager, '_tools'):
                    tools = tool_manager._tools
                    logger.info(f"Found {len(tools)} tools from _tool_manager._tools")
            except Exception as e:
                logger.debug(f"Error accessing _tool_manager: {e}")

        # Access prompt manager directly  
        if hasattr(mcp_server, '_prompt_manager'):
            try:
                prompt_manager = mcp_server._prompt_manager
                if hasattr(prompt_manager, '_prompts'):
                    prompts = prompt_manager._prompts
                    logger.info(f"Found {len(prompts)} prompts from _prompt_manager._prompts")
            except Exception as e:
                logger.debug(f"Error accessing _prompt_manager: {e}")
        
        logger.info("=" * 60)
        logger.info("YNAB MCP SERVER STARTUP - REGISTERED RESOURCES")
        logger.info("=" * 60)
        
        # Log tools
        if tools:
            logger.info(f"🔧 REGISTERED TOOLS ({len(tools)}):")
            for tool_name, tool_obj in tools.items():
                # Get description from the tool object
                description = "No description available"
                if hasattr(tool_obj, 'description') and tool_obj.description:
                    # Get just the first line of the description
                    description = tool_obj.description.strip().split('\n')[0]
                elif hasattr(tool_obj, 'fn') and hasattr(tool_obj.fn, '__doc__') and tool_obj.fn.__doc__:
                    # Fallback to function docstring
                    description = tool_obj.fn.__doc__.strip().split('\n')[0]
                    
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