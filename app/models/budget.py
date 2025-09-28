"""
Budget-related models
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CurrencyFormat(BaseModel):
    """Currency format information"""
    iso_code: str
    example_format: str
    decimal_digits: int
    decimal_separator: str
    symbol_first: bool
    group_separator: str
    currency_symbol: str
    display_symbol: bool


class DateFormat(BaseModel):
    """Date format information"""
    format: str


class BudgetSummary(BaseModel):
    """Budget summary information"""
    id: str
    name: str
    last_modified_on: Optional[datetime] = None
    first_month: Optional[str] = None  # Date string in YYYY-MM-DD format
    last_month: Optional[str] = None   # Date string in YYYY-MM-DD format
    date_format: Optional[DateFormat] = None
    currency_format: Optional[CurrencyFormat] = None


class Budget(BudgetSummary):
    """Complete budget information with all related entities"""
    accounts: List["Account"] = Field(default_factory=list)
    payees: List["Payee"] = Field(default_factory=list)
    category_groups: List["CategoryGroup"] = Field(default_factory=list)
    categories: List["Category"] = Field(default_factory=list)
    transactions: List["Transaction"] = Field(default_factory=list)
    server_knowledge: Optional[int] = None


# Import to resolve forward references
from .account import Account
from .payee import Payee  
from .category import Category, CategoryGroup
from .transaction import Transaction

Budget.model_rebuild()