"""Search/fetch tools matching the MCP company-knowledge schema.

ChatGPT Business/Enterprise's "Company knowledge" feature only treats apps as
citable sources if they expose tools named exactly `search` and `fetch` whose
input schemas match `{query: str}` and `{id: str}` respectively. We index
accounts, categories, and payees from the last-used budget so the LLM can cite
specific entities.
"""

from __future__ import annotations

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from app.dependencies import get_ynab_service
from app.exceptions import BudgetNotFoundException
from app.services import YNABService

_ID_SEPARATOR = "|"


def _make_id(entity_type: str, budget_id: str, entity_id: str) -> str:
    return f"{entity_type}{_ID_SEPARATOR}{budget_id}{_ID_SEPARATOR}{entity_id}"


def _parse_id(combined: str) -> tuple[str, str, str]:
    parts = combined.split(_ID_SEPARATOR, 2)
    if len(parts) != 3:
        raise ToolError(f"Malformed id: {combined!r}")
    return parts[0], parts[1], parts[2]


def _ynab_url(entity_type: str, budget_id: str, entity_id: str) -> str:
    """Canonical YNAB.com URL for citation. The entity-specific paths aren't
    individually addressable, so we link to the relevant section of the budget."""
    base = f"https://app.ynab.com/{budget_id}"
    section = {
        "account": "accounts",
        "category": "budget",
        "payee": "all-spending",
    }.get(entity_type, "")
    return f"{base}/{section}" if section else base


@tool(
    name="search",
    tags={"search", "readonly", "knowledge"},
    annotations={
        "title": "Search YNAB",
        "readOnlyHint": True,
        "openWorldHint": False,
    },
    timeout=30.0,
)
async def search(
    query: str,
    service: YNABService = Depends(get_ynab_service),
) -> dict:
    """Search across YNAB accounts, categories, and payees in the last-used budget.

    Returns matches as citable knowledge sources for ChatGPT.

    Args:
        query: Free-text search term, matched case-insensitively against entity names.
    """
    needle = query.lower().strip()
    budget_id = "last-used"

    try:
        accounts = await service.get_accounts(budget_id)
        categories = await service.get_categories(budget_id)
        payees = await service.get_payees(budget_id)
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e

    results: list[dict] = []
    for a in accounts:
        if needle in a.name.lower():
            results.append({
                "id": _make_id("account", budget_id, a.id),
                "title": f"Account: {a.name}",
                "url": _ynab_url("account", budget_id, a.id),
            })
    for c in categories:
        if needle in c.name.lower():
            results.append({
                "id": _make_id("category", budget_id, c.id),
                "title": f"Category: {c.name}",
                "url": _ynab_url("category", budget_id, c.id),
            })
    for p in payees:
        if p.name and needle in p.name.lower():
            results.append({
                "id": _make_id("payee", budget_id, p.id),
                "title": f"Payee: {p.name}",
                "url": _ynab_url("payee", budget_id, p.id),
            })

    return {"results": results[:25]}


@tool(
    name="fetch",
    tags={"fetch", "readonly", "knowledge"},
    annotations={
        "title": "Fetch YNAB entity",
        "readOnlyHint": True,
        "openWorldHint": False,
    },
    timeout=30.0,
)
async def fetch(
    id: str,
    service: YNABService = Depends(get_ynab_service),
) -> dict:
    """Fetch the full details for a YNAB entity returned by `search`.

    Args:
        id: Opaque id from a prior `search` result.
    """
    entity_type, budget_id, entity_id = _parse_id(id)

    try:
        if entity_type == "account":
            account = await service.get_account(budget_id, entity_id)
            text_lines = [
                f"Account: {account.name}",
                f"Type: {account.type.value}",
                f"On budget: {account.on_budget}",
                f"Balance: ${account.balance / 1000:,.2f}",
                f"Cleared balance: ${account.cleared_balance / 1000:,.2f}",
                f"Closed: {account.closed}",
            ]
            if account.note:
                text_lines.append(f"Notes: {account.note}")
            return {
                "id": id,
                "title": f"Account: {account.name}",
                "text": "\n".join(text_lines),
                "url": _ynab_url(entity_type, budget_id, entity_id),
                "metadata": {
                    "entity_type": entity_type,
                    "budget_id": budget_id,
                    "account_id": entity_id,
                },
            }
        if entity_type == "category":
            categories = await service.get_categories(budget_id)
            category = next((c for c in categories if c.id == entity_id), None)
            if category is None:
                raise ToolError(f"Category {entity_id} not found in budget {budget_id}")
            return {
                "id": id,
                "title": f"Category: {category.name}",
                "text": (
                    f"Category: {category.name}\n"
                    f"Group: {category.category_group_name}\n"
                    f"Budgeted: ${category.budgeted / 1000:,.2f}\n"
                    f"Activity: ${category.activity / 1000:,.2f}\n"
                    f"Balance: ${category.balance / 1000:,.2f}"
                ),
                "url": _ynab_url(entity_type, budget_id, entity_id),
                "metadata": {
                    "entity_type": entity_type,
                    "budget_id": budget_id,
                    "category_id": entity_id,
                },
            }
        if entity_type == "payee":
            payees = await service.get_payees(budget_id)
            payee = next((p for p in payees if p.id == entity_id), None)
            if payee is None:
                raise ToolError(f"Payee {entity_id} not found in budget {budget_id}")
            return {
                "id": id,
                "title": f"Payee: {payee.name}",
                "text": f"Payee: {payee.name}\nID: {payee.id}",
                "url": _ynab_url(entity_type, budget_id, entity_id),
                "metadata": {
                    "entity_type": entity_type,
                    "budget_id": budget_id,
                    "payee_id": entity_id,
                },
            }
    except BudgetNotFoundException as e:
        raise ToolError(f"Budget {e.budget_id} not found") from e

    raise ToolError(f"Unknown entity type: {entity_type!r}")
