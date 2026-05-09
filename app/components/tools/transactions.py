"""Transaction-related MCP tools."""

from typing import Literal

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from app.dependencies import get_ynab_service
from app.exceptions import (
    AccountNotFoundException,
    BudgetNotFoundException,
    CategoryNotFoundException,
    PayeeNotFoundException,
)
from app.models import TransactionDetail
from app.responses import TransactionListResponse
from app.services import YNABService

ClearedStatus = Literal["cleared", "uncleared", "reconciled"]
FlagColor = Literal["red", "orange", "yellow", "green", "blue", "purple"]
TransactionType = Literal["uncategorized", "unapproved"]


def _is_memo_empty(memo: str | None) -> bool:
    return memo is None or memo.strip() == ""


def _matches_payee(transaction: TransactionDetail, payee_id: list[str] | str) -> bool:
    if isinstance(payee_id, list):
        return transaction.payee_id in payee_id
    return transaction.payee_id == payee_id


def _filter_by_memo(
    transactions: list[TransactionDetail], empty_memo: bool | None
) -> list[TransactionDetail]:
    if empty_memo is None:
        return transactions
    if empty_memo:
        return [t for t in transactions if _is_memo_empty(t.memo)]
    return [t for t in transactions if not _is_memo_empty(t.memo)]


@tool(
    tags={"transactions", "readonly", "data-cleanup"},
    annotations={
        "title": "Get Transactions",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=60.0,
)
async def get_transactions(
    budget_id: str = "last-used",
    account_id: str | None = None,
    payee_id: list[str] | str | None = None,
    category_id: str | None = None,
    since_date: str | None = None,
    transaction_type: TransactionType | None = None,
    empty_memo: bool | None = None,
    service: YNABService = Depends(get_ynab_service),
) -> TransactionListResponse:
    """Get transactions for a specific budget with smart compound filtering.

    Picks the most efficient YNAB endpoint based on which filters are set, then
    applies any remaining filters in-memory.

    Filter priority:
    1. Account + any other filters → account endpoint, rest filtered in-memory
    2. Category + Payee → category endpoint, payee filtered in-memory
    3. Category only → category endpoint
    4. Payee only → payee endpoint (one call per payee for lists)
    5. No filters → general transactions endpoint

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
        account_id: Optional account ID to filter transactions for a specific account.
        payee_id: Optional payee ID or list of payee IDs to filter on.
        category_id: Optional category ID to filter on.
        since_date: Optional date filter (YYYY-MM-DD).
        transaction_type: Optional 'uncategorized' or 'unapproved' filter.
        empty_memo: True to find transactions missing memos; False to find transactions
            that have memo text. Useful for data-cleanup workflows.
    """
    try:
        if account_id:
            transactions = await service.get_transactions(
                budget_id,
                account_id=account_id,
                since_date=since_date,
                transaction_type=transaction_type,
            )
            if payee_id:
                transactions = [t for t in transactions if _matches_payee(t, payee_id)]
            if category_id:
                transactions = [t for t in transactions if t.category_id == category_id]
            transactions = _filter_by_memo(transactions, empty_memo)

        elif category_id:
            transactions = await service.get_category_transactions(
                budget_id,
                category_id,
                since_date=since_date,
                transaction_type=transaction_type,
            )
            if payee_id:
                transactions = [t for t in transactions if _matches_payee(t, payee_id)]
            transactions = _filter_by_memo(transactions, empty_memo)

        elif payee_id:
            if isinstance(payee_id, list):
                transactions = []
                for single in payee_id:
                    transactions.extend(
                        await service.get_payee_transactions(
                            budget_id,
                            single,
                            since_date=since_date,
                            transaction_type=transaction_type,
                        )
                    )
            else:
                transactions = await service.get_payee_transactions(
                    budget_id,
                    payee_id,
                    since_date=since_date,
                    transaction_type=transaction_type,
                )
            transactions = _filter_by_memo(transactions, empty_memo)

        else:
            transactions = await service.get_transactions(
                budget_id,
                since_date=since_date,
                transaction_type=transaction_type,
            )
            transactions = _filter_by_memo(transactions, empty_memo)

    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e
    except AccountNotFoundException as e:
        raise ToolError(f"Account {e.account_id} not found") from e
    except PayeeNotFoundException as e:
        raise ToolError(f"Payee {e.payee_id} not found") from e
    except CategoryNotFoundException as e:
        raise ToolError(f"Category {e.category_id} not found") from e

    return TransactionListResponse(
        transactions=transactions,
        count=len(transactions),
        budget_id=budget_id,
        account_id=account_id,
        payee_id=payee_id,
        category_id=category_id,
        empty_memo=empty_memo,
    )


@tool(
    tags={"transactions", "editing", "modify"},
    annotations={
        "title": "Update Transaction Details",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
    timeout=30.0,
)
async def update_transaction(
    budget_id: str,
    transaction_id: str,
    memo: str | None = None,
    amount: float | None = None,
    payee_id: str | None = None,
    payee_name: str | None = None,
    category_id: str | None = None,
    cleared: ClearedStatus | None = None,
    approved: bool | None = None,
    flag_color: FlagColor | None = None,
    date: str | None = None,
    service: YNABService = Depends(get_ynab_service),
) -> TransactionDetail:
    """Update an existing transaction with new details.

    Use this to modify transaction information like adding memos, changing amounts,
    updating categories, or marking transactions as cleared. All parameters are
    optional - only provide the fields you want to update.

    Args:
        budget_id: The ID of the budget.
        transaction_id: The ID of the transaction to update.
        memo: Transaction memo/description (max 500 characters).
        amount: Amount in standard currency format (e.g., 50.00 for $50.00, -25.99 for expenses).
        payee_id: Payee ID (use get_payees or find_payee_by_name to find valid IDs).
        payee_name: Payee name (alternative to payee_id; will create payee if it doesn't exist).
        category_id: Category ID (use get_categories to find valid IDs).
        cleared: Cleared status — 'cleared', 'uncleared', or 'reconciled'.
        approved: Whether transaction is approved (False for transactions needing review).
        flag_color: Visual flag color for organization.
        date: Transaction date in YYYY-MM-DD format.
    """
    amount_milliunits = int(amount * 1000) if amount is not None else None

    try:
        return await service.update_transaction(
            budget_id=budget_id,
            transaction_id=transaction_id,
            memo=memo,
            amount=amount_milliunits,
            payee_id=payee_id,
            payee_name=payee_name,
            category_id=category_id,
            cleared=cleared,
            approved=approved,
            flag_color=flag_color,
            date=date,
        )
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e
