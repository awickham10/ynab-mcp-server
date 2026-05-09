"""Interactive widget for categorizing and approving pending YNAB transactions.

The LLM passes per-transaction category suggestions when invoking the tool;
the widget renders one row per pending transaction with the suggested
category pre-selected. Each row's Approve button calls a backend tool that
applies the change against YNAB and removes the row from the queue. A
bulk-approve action commits every row's current selection in one batch.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCPApp
from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from prefab_ui.actions import PopState, SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    Column,
    Combobox,
    ComboboxGroup,
    ComboboxLabel,
    ComboboxOption,
    Else,
    ForEach,
    H2,
    H3,
    If,
    Markdown,
    Muted,
    Row,
    Span,
    Text,
)
from prefab_ui.rx import Rx

from app.dependencies import get_ynab_service
from app.exceptions import BudgetNotFoundException
from app.services import YNABService

categorize_queue_app = FastMCPApp("categorize_queue")


# ---------------------------------------------------------------------------
# Backend tool — invoked by the widget
# ---------------------------------------------------------------------------


@categorize_queue_app.tool()
async def submit_categorizations(
    budget_id: str,
    items: list[dict[str, str]],
    service: YNABService = Depends(get_ynab_service),
) -> dict[str, Any]:
    """Apply category + approval changes to one or more YNAB transactions.

    Args:
        budget_id: The budget the transactions belong to.
        items: List of {"transaction_id": ..., "category_id": ...} updates.
            Each item is also marked approved as part of the same patch.
    """
    if not items:
        return {"updated": 0}

    updates = []
    for item in items:
        # The widget sends the whole queue row dict, which uses `id`. The model
        # may also call this directly with `transaction_id`. Accept either.
        txn_id = item.get("transaction_id") or item.get("id")
        if not txn_id:
            continue
        updates.append({
            "id": txn_id,
            "category_id": item.get("category_id") or None,
            "approved": True,
        })
    try:
        result = await service.bulk_update_transactions(budget_id, updates)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e

    return {
        "updated": len(result.get("transaction_ids", [])),
        "duplicates": len(result.get("duplicate_import_ids", [])),
    }


# ---------------------------------------------------------------------------
# UI entry-point — invoked by the model
# ---------------------------------------------------------------------------


def _format_currency(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _category_options(categories: list, selected: str | None) -> list:
    """Group categories by their parent group, ready for ComboboxGroup."""
    by_group: dict[str, list] = {}
    for cat in categories:
        by_group.setdefault(cat.category_group_name or "Other", []).append(cat)
    return by_group


@categorize_queue_app.ui(
    title="Categorize transactions",
    description=(
        "Renders an interactive queue of pending YNAB transactions (uncategorized "
        "or unapproved) so the user can categorize and approve them in one flow. "
        "Pass a `suggestions` dict mapping transaction_id -> category_id with "
        "your best guess per row; the widget pre-selects them. Optionally pass "
        "`notes` mapping transaction_id -> short reasoning string shown next to "
        "the row. Use this when the user asks to clean up, categorize, approve, "
        "or process pending transactions."
    ),
    tags={"transactions", "categorize", "approve", "readonly"},
    annotations={
        "readOnlyHint": True,
        "openWorldHint": False,
        "destructiveHint": False,
    },
    timeout=60.0,
)
async def categorize_queue(
    budget_id: str = "last-used",
    suggestions: dict[str, str] | None = None,
    notes: dict[str, str] | None = None,
    service: YNABService = Depends(get_ynab_service),
) -> Column:
    """Render the categorize-and-approve queue.

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
        suggestions: Optional mapping of transaction_id -> category_id with the
            LLM's best categorization suggestion per row. Pre-selects the
            dropdown so the user just confirms.
        notes: Optional mapping of transaction_id -> short reasoning string,
            shown beneath each row to explain the suggestion.
    """
    suggestions = suggestions or {}
    notes = notes or {}

    accounts, unapproved, uncategorized, all_categories = await asyncio.gather(
        service.get_accounts(budget_id),
        service.get_transactions(budget_id, transaction_type="unapproved"),
        service.get_transactions(budget_id, transaction_type="uncategorized"),
        service.get_categories(budget_id),
    )

    actionable_account_ids = {
        a.id for a in accounts if a.on_budget and not a.closed and not a.deleted
    }

    pending: dict[str, Any] = {}
    for t in unapproved:
        if t.account_id in actionable_account_ids:
            pending[t.id] = t
    for t in uncategorized:
        if (
            t.transfer_account_id is None
            and t.payee_name != "Starting Balance"
            and t.account_id in actionable_account_ids
        ):
            pending[t.id] = t

    pending_list = sorted(pending.values(), key=lambda t: t.date, reverse=True)

    categories = [
        c
        for c in all_categories
        if not c.hidden and not c.deleted and c.category_group_name != "Internal Master Category"
    ]
    grouped_categories = _category_options(categories, None)

    initial_rows = [
        {
            "id": t.id,
            "date": t.date,
            "payee": t.payee_name or "(no payee)",
            "amount": t.amount / 1000.0,
            "amount_label": _format_currency(t.amount / 1000.0),
            "memo": t.memo or "",
            "category_id": suggestions.get(t.id) or t.category_id or "",
            "had_suggestion": bool(suggestions.get(t.id)),
            "note": notes.get(t.id, ""),
        }
        for t in pending_list
    ]

    suggested_count = sum(1 for t in pending_list if suggestions.get(t.id))

    with Column(gap=4, let={"queue": initial_rows}) as page:
        H2("Approve or categorize transactions")

        with If("queue.length === 0"):
            Markdown("**All caught up.** No pending transactions in your active accounts.")

        with Else():
            with Row(gap=3):
                Muted("{{ queue.length }} pending")
                if suggested_count:
                    Badge(
                        f"{suggested_count} pre-suggested",
                        variant="secondary",
                    )
                Button(
                    "Approve all with current selections",
                    variant="default",
                    onClick=[
                        CallTool(
                            "submit_categorizations",
                            arguments={
                                "budget_id": budget_id,
                                "items": Rx("queue"),
                            },
                            onSuccess=[
                                SetState("queue", []),
                                ShowToast("Approved everything in the queue"),
                            ],
                            onError=ShowToast("Bulk approve failed — try one at a time"),
                        )
                    ],
                )

            with ForEach("queue") as (idx, txn):
                with Card():
                    with CardHeader():
                        with Row(gap=3):
                            CardTitle(txn.payee)
                            Span(txn["date"])
                            Span(txn.amount_label)
                        with If(txn.note != ""):
                            CardDescription(txn.note)
                        with If(txn.memo != ""):
                            Muted(f"Memo: {txn.memo}")
                    with CardContent():
                        with Row(gap=3):
                            with Combobox(
                                name=f"queue.{idx}.category_id",
                                placeholder="Pick a category…",
                                searchPlaceholder="Search categories",
                            ):
                                for group_name, group_cats in grouped_categories.items():
                                    with ComboboxGroup():
                                        ComboboxLabel(group_name)
                                        for cat in group_cats:
                                            ComboboxOption(
                                                cat.name,
                                                value=cat.id,
                                            )
                            Button(
                                "Approve",
                                variant="success",
                                disabled=txn.category_id == "",
                                onClick=[
                                    CallTool(
                                        "submit_categorizations",
                                        arguments={
                                            "budget_id": budget_id,
                                            "items": [
                                                {
                                                    "transaction_id": txn.id,
                                                    "category_id": txn.category_id,
                                                }
                                            ],
                                        },
                                        onSuccess=[
                                            PopState("queue", index=idx),
                                            ShowToast("Approved"),
                                        ],
                                        onError=ShowToast("Update failed"),
                                    )
                                ],
                            )
                            Button(
                                "Skip",
                                variant="ghost",
                                onClick=PopState("queue", index=idx),
                            )

    return page
