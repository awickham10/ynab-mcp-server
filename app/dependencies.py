"""Shared FastMCP dependency providers."""

import httpx
from fastmcp.dependencies import CurrentAccessToken
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.dependencies import get_context

from app.services import YNABService


def get_http_client() -> httpx.AsyncClient:
    """Return the shared httpx.AsyncClient from the lifespan context."""
    return get_context().lifespan_context["http_client"]


def get_ynab_service(token: AccessToken = CurrentAccessToken()) -> YNABService:
    """Build a YNABService bound to the current request's access token."""
    return YNABService(token.token, get_http_client())
