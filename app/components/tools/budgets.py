"""Budget-related MCP tools."""

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from app.dependencies import get_ynab_service
from app.exceptions import BudgetNotFoundException
from app.models import Budget
from app.responses import BudgetListResponse
from app.services import YNABService


@tool(
    tags={"budget", "overview", "readonly"},
    annotations={
        "title": "Get All Budgets",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def get_budgets(
    include_accounts: bool = False,
    service: YNABService = Depends(get_ynab_service),
) -> BudgetListResponse:
    """Get all budgets for the authenticated user.

    Args:
        include_accounts: Whether to include account summaries in the response.
    """
    budgets = await service.get_budgets(include_accounts=include_accounts)
    return BudgetListResponse(budgets=budgets, count=len(budgets))


@tool(
    tags={"budget", "details", "readonly"},
    annotations={
        "title": "Get Budget Details",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def get_budget(
    budget_id: str = "last-used",
    service: YNABService = Depends(get_ynab_service),
) -> Budget:
    """Get detailed information for a specific budget.

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
    """
    try:
        return await service.get_budget(budget_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e
