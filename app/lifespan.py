"""Server-level lifespan hooks."""

import httpx
from fastmcp.server.lifespan import lifespan

from app.config import config


@lifespan
async def http_client_lifespan(server):
    """Provide a shared httpx.AsyncClient for the lifetime of the server."""
    async with httpx.AsyncClient(timeout=config.request_timeout) as client:
        yield {"http_client": client}
