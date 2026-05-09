"""Spending analysis MCP tool."""

from datetime import datetime, timedelta

from fastmcp import Context
from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from app.dependencies import get_ynab_service
from app.exceptions import BudgetNotFoundException
from app.responses import SpendingAnalysisResponse, TopSpendingCategory
from app.services import YNABService


@tool(
    tags={"analytics", "spending", "insights", "readonly"},
    annotations={
        "title": "Analyze Spending Patterns",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    timeout=60.0,
)
async def analyze_spending(
    ctx: Context,
    budget_id: str = "last-used",
    months: int = 3,
    service: YNABService = Depends(get_ynab_service),
) -> SpendingAnalysisResponse:
    """Analyze spending patterns and trends for a budget over a specified time period.

    Provides insights into spending habits including total spending, top categories,
    transaction counts, and daily averages. Use this when users want to understand
    their spending behavior, identify areas of high spending, or get budget insights.

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
        months: Number of months to analyze going back from today (default: 3, max recommended: 12).
    """
    since_date = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")

    await ctx.info(f"Fetching transactions since {since_date}")
    await ctx.report_progress(progress=10, total=100)

    try:
        transactions = await service.get_transactions(budget_id, since_date=since_date)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e

    await ctx.report_progress(progress=60, total=100)

    total_spending = sum(t.amount for t in transactions if t.amount < 0)
    category_spending: dict[str, int] = {}
    for transaction in transactions:
        if transaction.amount < 0 and transaction.category_name:
            category_spending[transaction.category_name] = (
                category_spending.get(transaction.category_name, 0) + abs(transaction.amount)
            )

    top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:10]

    await ctx.report_progress(progress=100, total=100)

    return SpendingAnalysisResponse(
        analysis_period_days=30 * months,
        total_spending_milliunits=abs(total_spending),
        total_spending_formatted=abs(total_spending) / 1000.0,
        transaction_count=sum(1 for t in transactions if t.amount < 0),
        top_spending_categories=[
            TopSpendingCategory(
                category=name,
                amount_milliunits=amount,
                amount_formatted=amount / 1000.0,
            )
            for name, amount in top_categories
        ],
        average_daily_spending=(abs(total_spending) / (30 * months) / 1000.0) if total_spending else 0.0,
    )
