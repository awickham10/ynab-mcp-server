"""Payee-related MCP tools."""

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from app.dependencies import get_ynab_service
from app.exceptions import BudgetNotFoundException
from app.responses import PayeeListResponse, PayeeSearchResponse
from app.services import YNABService


@tool(
    tags={"payees", "merchants", "readonly"},
    annotations={
        "title": "Get All Payees",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def get_payees(
    budget_id: str = "last-used",
    service: YNABService = Depends(get_ynab_service),
) -> PayeeListResponse:
    """Get all payees (merchants, people, places) for a specific budget.

    Returns all entities that have been paid money to or received money from. Use
    this when you need payee IDs for filtering transactions, or when users want to
    see all the places they spend money (restaurants, stores, etc.).

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
    """
    try:
        payees = await service.get_payees(budget_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e
    return PayeeListResponse(payees=payees, count=len(payees))


@tool(
    tags={"payees", "search", "readonly"},
    annotations={
        "title": "Find Payee by Name",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def find_payee_by_name(
    payee_name: str,
    budget_id: str = "last-used",
    service: YNABService = Depends(get_ynab_service),
) -> PayeeSearchResponse:
    """Find payees by name using case-insensitive partial matching.

    Use this when you need to search for payees without knowing their exact name or
    ID. Particularly useful for finding payees when users provide partial names,
    common names, or slight variations of business names (e.g., "Starbucks",
    "starbucks", "Star").

    Args:
        payee_name: The name or partial name of the payee to search for (case-insensitive).
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
    """
    try:
        all_payees = await service.get_payees(budget_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e

    search_term = payee_name.lower().strip()
    matching = [p for p in all_payees if p.name and search_term in p.name.lower()]

    return PayeeSearchResponse(
        payees=matching,
        count=len(matching),
        search_term=payee_name,
        budget_id=budget_id,
    )
