"""Interactive widget for categorizing and approving pending YNAB transactions.

The LLM passes per-transaction category suggestions when invoking the tool;
the widget renders one row per pending transaction with the suggested
category pre-selected. Each row's Approve button calls a backend tool that
applies the change against YNAB and removes the row from the queue. A
bulk-approve action commits every row's current selection in one batch.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from fastmcp import FastMCPApp
from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from prefab_ui.actions import SetState, ShowToast
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
    H2,
    If,
    Markdown,
    Muted,
    Row,
    Span,
)
from prefab_ui.rx import Rx

from app.dependencies import get_ynab_service
from app.exceptions import BudgetNotFoundException
from app.models import TransactionDetail
from app.services import YNABService

categorize_queue_app = FastMCPApp("categorize_queue")

# Default page size — 150 transactions × 50 categories each is too much DOM,
# so cap how many rows we render at once. The model can call again for the
# next batch (or pass a higher limit explicitly).
DEFAULT_LIMIT = 25
MAX_LIMIT = 100


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
        txn_id = item.get("transaction_id") or item.get("id")
        if not txn_id:
            continue
        updates.append({
            "id": txn_id,
            "category_id": item.get("category_id") or None,
            "approved": True,
        })

    if not updates:
        return {"updated": 0}

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


def _safe_state_key(transaction_id: str) -> str:
    """State keys must be `[A-Za-z_][A-Za-z0-9_]*`. UUIDs have hyphens; sanitize."""
    return "txn_" + re.sub(r"[^A-Za-z0-9]", "_", transaction_id)


def _group_categories(categories: list) -> dict[str, list]:
    by_group: dict[str, list] = {}
    for cat in categories:
        by_group.setdefault(cat.category_group_name or "Other", []).append(cat)
    return by_group


def _build_pending(
    accounts: list,
    unapproved: list[TransactionDetail],
    uncategorized: list[TransactionDetail],
) -> list[TransactionDetail]:
    """Same union YNAB's UI uses for 'X transactions to approve or categorize'."""
    actionable = {a.id for a in accounts if a.on_budget and not a.closed and not a.deleted}
    pending: dict[str, TransactionDetail] = {}
    for t in unapproved:
        if t.account_id in actionable:
            pending[t.id] = t
    for t in uncategorized:
        if (
            t.transfer_account_id is None
            and t.payee_name != "Starting Balance"
            and t.account_id in actionable
        ):
            pending[t.id] = t
    return sorted(pending.values(), key=lambda t: t.date, reverse=True)


@categorize_queue_app.ui(
    title="Categorize transactions",
    description=(
        "Renders an interactive queue of pending YNAB transactions (uncategorized "
        "or unapproved) so the user can categorize and approve them in one flow. "
        "Pass a `suggestions` dict mapping transaction_id -> category_id with "
        "your best guess per row; the widget pre-selects them. Optionally pass "
        "`notes` mapping transaction_id -> short reasoning string shown next to "
        "the row. The widget shows up to `limit` transactions at a time "
        f"(default {DEFAULT_LIMIT}); call again with a higher limit or after "
        "the first batch is processed to load more. Use this when the user "
        "asks to clean up, categorize, approve, or process pending transactions."
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
    limit: int = DEFAULT_LIMIT,
    service: YNABService = Depends(get_ynab_service),
) -> Column:
    """Render the categorize-and-approve queue.

    Args:
        budget_id: The ID of the budget (use 'last-used' for the most recent budget).
        suggestions: Optional mapping of transaction_id -> category_id with the
            LLM's best categorization suggestion per row. Pre-selects the dropdown.
        notes: Optional mapping of transaction_id -> short reasoning string,
            shown beneath each row to explain the suggestion.
        limit: Max rows to render. Capped at 100 to avoid runaway DOM size.
    """
    suggestions = suggestions or {}
    notes = notes or {}
    limit = max(1, min(limit, MAX_LIMIT))

    accounts, unapproved, uncategorized, all_categories = await asyncio.gather(
        service.get_accounts(budget_id),
        service.get_transactions(budget_id, transaction_type="unapproved"),
        service.get_transactions(budget_id, transaction_type="uncategorized"),
        service.get_categories(budget_id),
    )

    pending = _build_pending(accounts, unapproved, uncategorized)
    total_pending = len(pending)
    visible = pending[:limit]

    categories = [
        c
        for c in all_categories
        if not c.hidden
        and not c.deleted
        and c.category_group_name != "Internal Master Category"
    ]
    grouped = _group_categories(categories)

    suggested_count = sum(1 for t in visible if suggestions.get(t.id))

    # Build the initial state block keyed by sanitized transaction id. Per-row
    # state lives at fixed keys (no template paths) so Combobox bindings
    # resolve cleanly and the LLM's suggestions actually pre-select.
    initial_state: dict[str, Any] = {}
    for t in visible:
        key = _safe_state_key(t.id)
        initial_state[f"{key}_category"] = (
            suggestions.get(t.id) or t.category_id or ""
        )
        initial_state[f"{key}_visible"] = True

    with Column(gap=4, let=initial_state) as page:
        H2("Approve or categorize transactions")

        if total_pending == 0:
            Markdown(
                "**All caught up.** No pending transactions in your active accounts."
            )
            return page

        # Header summary
        with Row(gap=3):
            Muted(
                f"Showing {len(visible)} of {total_pending} pending"
                if total_pending > len(visible)
                else f"{total_pending} pending"
            )
            if suggested_count:
                Badge(f"{suggested_count} pre-suggested", variant="secondary")

        # Bulk-approve current page
        Button(
            f"Approve all {len(visible)} with current selections",
            variant="default",
            onClick=[
                CallTool(
                    "submit_categorizations",
                    arguments={
                        "budget_id": budget_id,
                        "items": [
                            {
                                "transaction_id": t.id,
                                "category_id": Rx(
                                    f"{_safe_state_key(t.id)}_category"
                                ),
                            }
                            for t in visible
                        ],
                    },
                    onSuccess=(
                        [
                            SetState(f"{_safe_state_key(t.id)}_visible", False)
                            for t in visible
                        ]
                        + [ShowToast("Approved current page")]
                    ),
                    onError=ShowToast("Bulk approve failed — try one at a time"),
                )
            ],
        )

        for t in visible:
            key = _safe_state_key(t.id)
            category_state = f"{key}_category"
            visible_state = f"{key}_visible"

            with If(visible_state):
                with Card():
                    with CardHeader():
                        with Row(gap=3):
                            CardTitle(t.payee_name or "(no payee)")
                            Span(t.date)
                            Span(_format_currency(t.amount / 1000.0))
                        if notes.get(t.id):
                            CardDescription(notes[t.id])
                        if t.memo:
                            Muted(f"Memo: {t.memo}")
                    with CardContent():
                        with Row(gap=3):
                            with Combobox(
                                name=category_state,
                                placeholder="Pick a category…",
                                searchPlaceholder="Search categories",
                            ):
                                for group_name, group_cats in grouped.items():
                                    with ComboboxGroup():
                                        ComboboxLabel(group_name)
                                        for cat in group_cats:
                                            ComboboxOption(cat.name, value=cat.id)
                            Button(
                                "Approve",
                                variant="success",
                                disabled=Rx(category_state) == "",
                                onClick=[
                                    CallTool(
                                        "submit_categorizations",
                                        arguments={
                                            "budget_id": budget_id,
                                            "items": [
                                                {
                                                    "transaction_id": t.id,
                                                    "category_id": Rx(category_state),
                                                }
                                            ],
                                        },
                                        onSuccess=[
                                            SetState(visible_state, False),
                                            ShowToast("Approved"),
                                        ],
                                        onError=ShowToast("Update failed"),
                                    )
                                ],
                            )
                            Button(
                                "Skip",
                                variant="ghost",
                                onClick=SetState(visible_state, False),
                            )

    return page
