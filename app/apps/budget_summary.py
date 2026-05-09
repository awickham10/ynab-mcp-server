"""Interactive budget summary dashboard rendered as a ChatGPT App.

Uses FastMCPApp + prefab-ui so the Python tool function returns Prefab
Components, FastMCP synthesizes the renderer resource, and ChatGPT renders
the dashboard inside its iframe sandbox.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastmcp import FastMCPApp
from fastmcp.dependencies import Depends
from prefab_ui.components import (
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    Column,
    DataTable,
    DataTableColumn,
    Grid,
    GridItem,
    H2,
    Metric,
    Muted,
)

from app.dependencies import get_ynab_service
from app.services import YNABService

budget_summary_app = FastMCPApp("budget_summary")


def _format_currency(milliunits: int) -> str:
    """YNAB stores amounts in milliunits (1 USD = 1000)."""
    return f"${milliunits / 1000:,.2f}"


@budget_summary_app.ui(
    title="YNAB Budget Summary",
    description=(
        "Renders an interactive dashboard with current account balances, top "
        "spending categories over the last 30 days, and the count of "
        "transactions waiting to be approved or categorized. Use this when "
        "the user asks for a budget overview, account balances, or a snapshot "
        "of where their money is going."
    ),
    tags={"budget", "dashboard", "readonly"},
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "destructiveHint": False,
    },
    timeout=60.0,
)
async def show_budget_summary(
    budget_id: str = "last-used",
    service: YNABService = Depends(get_ynab_service),
) -> Column:
    """Render the budget summary dashboard for ChatGPT.

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
    """
    budget = await service.get_budget(budget_id)
    accounts = await service.get_accounts(budget_id)
    since_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    transactions = await service.get_transactions(budget_id, since_date=since_date)
    unapproved = await service.get_transactions(
        budget_id, transaction_type="unapproved"
    )

    actionable_account_ids = {
        a.id for a in accounts if a.on_budget and not a.closed and not a.deleted
    }

    cash_balance = sum(
        a.balance for a in accounts
        if a.on_budget and not a.closed and a.balance > 0
    )
    credit_debt = sum(
        -a.balance for a in accounts
        if a.on_budget and not a.closed and a.balance < 0
    )
    net_on_budget = sum(
        a.balance for a in accounts if a.on_budget and not a.closed
    )

    needs_action = {t.id for t in unapproved if t.account_id in actionable_account_ids}
    needs_action.update(
        t.id for t in transactions
        if t.category_id is None
        and t.transfer_account_id is None
        and t.payee_name != "Starting Balance"
        and t.account_id in actionable_account_ids
    )

    category_spending: dict[str, int] = {}
    for t in transactions:
        if t.amount < 0 and t.category_name and t.account_id in actionable_account_ids:
            category_spending[t.category_name] = (
                category_spending.get(t.category_name, 0) + abs(t.amount)
            )
    top_spending = sorted(
        category_spending.items(), key=lambda x: x[1], reverse=True
    )[:5]

    recent = sorted(
        (t for t in transactions if t.account_id in actionable_account_ids),
        key=lambda t: t.date,
        reverse=True,
    )[:10]

    with Column(gap=4) as page:
        H2(f"{budget.name}")
        Muted(f"Last activity: {budget.last_modified_on or 'unknown'}")

        with Grid(columns=4, gap=4):
            with GridItem():
                Metric(
                    label="Cash on hand",
                    value=_format_currency(cash_balance),
                    description="Sum of positive on-budget balances",
                )
            with GridItem():
                Metric(
                    label="Credit card debt",
                    value=_format_currency(credit_debt),
                    description="Sum of negative on-budget balances",
                    trend_sentiment="negative" if credit_debt > 0 else "neutral",
                )
            with GridItem():
                Metric(
                    label="Net (on-budget)",
                    value=_format_currency(net_on_budget),
                    trend="up" if net_on_budget >= 0 else "down",
                )
            with GridItem():
                Metric(
                    label="Needs action",
                    value=len(needs_action),
                    description="To approve or categorize",
                    trend_sentiment="negative" if needs_action else "positive",
                )

        with Card():
            with CardHeader():
                CardTitle("Top spending categories")
                CardDescription("Last 30 days, on-budget accounts only")
            with CardContent():
                if top_spending:
                    DataTable(
                        columns=[
                            DataTableColumn(key="category", header="Category", sortable=True),
                            DataTableColumn(key="spent", header="Spent", sortable=True),
                        ],
                        rows=[
                            {"category": name, "spent": _format_currency(amount)}
                            for name, amount in top_spending
                        ],
                    )
                else:
                    Muted("No categorized spending in the last 30 days.")

        with Card():
            with CardHeader():
                CardTitle("Recent transactions")
                CardDescription("Latest activity on on-budget accounts")
            with CardContent():
                if recent:
                    DataTable(
                        columns=[
                            DataTableColumn(key="date", header="Date", sortable=True),
                            DataTableColumn(key="payee", header="Payee"),
                            DataTableColumn(key="category", header="Category"),
                            DataTableColumn(key="amount", header="Amount", sortable=True),
                        ],
                        rows=[
                            {
                                "date": t.date,
                                "payee": t.payee_name or "—",
                                "category": t.category_name or "(uncategorized)",
                                "amount": _format_currency(t.amount),
                            }
                            for t in recent
                        ],
                        search=True,
                        paginated=True,
                        page_size=10,
                    )
                else:
                    Muted("No recent transactions.")

    return page
