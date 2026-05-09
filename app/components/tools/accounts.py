"""Account-related MCP tools."""

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from app.dependencies import get_ynab_service
from app.exceptions import AccountNotFoundException, BudgetNotFoundException
from app.models import Account
from app.responses import AccountListResponse
from app.services import YNABService


@tool(
    tags={"accounts", "balances", "readonly"},
    annotations={
        "title": "Get All Accounts",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def get_accounts(
    budget_id: str = "last-used",
    service: YNABService = Depends(get_ynab_service),
) -> AccountListResponse:
    """Get all accounts for a specific budget including balances and account types.

    Returns checking, savings, credit cards, and other account information. Use this
    to see account balances, account names, or when you need account IDs for filtering
    transactions by account.

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
    """
    try:
        accounts = await service.get_accounts(budget_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e
    return AccountListResponse(accounts=accounts, count=len(accounts))


@tool(
    tags={"accounts", "details", "readonly"},
    annotations={
        "title": "Get Account Details",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def get_account(
    budget_id: str,
    account_id: str,
    service: YNABService = Depends(get_ynab_service),
) -> Account:
    """Get information for a specific account.

    Args:
        budget_id: The ID of the budget.
        account_id: The ID of the account.
    """
    try:
        return await service.get_account(budget_id, account_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e
    except AccountNotFoundException as e:
        raise ToolError(f"Account {e.account_id} not found") from e
