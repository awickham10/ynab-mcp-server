"""Typed response models for MCP tool outputs."""

from pydantic import BaseModel

from app.models import (
    Account,
    Budget,
    BudgetSummary,
    Category,
    Payee,
    TransactionDetail,
)


class BudgetListResponse(BaseModel):
    budgets: list[BudgetSummary]
    count: int


class AccountListResponse(BaseModel):
    accounts: list[Account]
    count: int


class CategoryListResponse(BaseModel):
    categories: list[Category]
    count: int


class PayeeListResponse(BaseModel):
    payees: list[Payee]
    count: int


class PayeeSearchResponse(BaseModel):
    payees: list[Payee]
    count: int
    search_term: str
    budget_id: str


class TransactionListResponse(BaseModel):
    transactions: list[TransactionDetail]
    count: int
    budget_id: str
    account_id: str | None = None
    payee_id: list[str] | str | None = None
    category_id: str | None = None
    empty_memo: bool | None = None


class TopSpendingCategory(BaseModel):
    category: str
    amount_milliunits: int
    amount_formatted: float


class SpendingAnalysisResponse(BaseModel):
    analysis_period_days: int
    total_spending_milliunits: int
    total_spending_formatted: float
    transaction_count: int
    top_spending_categories: list[TopSpendingCategory]
    average_daily_spending: float


# Re-export model types tools return directly
__all__ = [
    "AccountListResponse",
    "Budget",
    "BudgetListResponse",
    "CategoryListResponse",
    "PayeeListResponse",
    "PayeeSearchResponse",
    "SpendingAnalysisResponse",
    "TopSpendingCategory",
    "TransactionDetail",
    "TransactionListResponse",
    "Account",
]
