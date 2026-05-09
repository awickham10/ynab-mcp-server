"""Category-related MCP tools."""

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from app.dependencies import get_ynab_service
from app.exceptions import BudgetNotFoundException
from app.responses import CategoryListResponse
from app.services import YNABService


@tool(
    tags={"categories", "budgeting", "readonly"},
    annotations={
        "title": "Get Budget Categories",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def get_categories(
    budget_id: str = "last-used",
    service: YNABService = Depends(get_ynab_service),
) -> CategoryListResponse:
    """Get all categories and category groups for a specific budget.

    Returns both category groups (like "Food", "Transportation") and individual
    categories (like "Groceries", "Gas"). Use this when you need category IDs for
    filtering transactions or when users ask about their budget categories and
    spending limits.

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
    """
    try:
        categories = await service.get_categories(budget_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e
    return CategoryListResponse(categories=categories, count=len(categories))
