"""
Account-related models
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, computed_field


class AccountType(str, Enum):
    """Account type enumeration"""
    CHECKING = "checking"
    SAVINGS = "savings"
    CASH = "cash"
    CREDIT_CARD = "creditCard"
    LINE_OF_CREDIT = "lineOfCredit"
    OTHER_ASSET = "otherAsset"
    OTHER_LIABILITY = "otherLiability"
    MORTGAGE = "mortgage"
    AUTO_LOAN = "autoLoan"
    STUDENT_LOAN = "studentLoan"
    PERSONAL_LOAN = "personalLoan"
    MEDICAL_DEBT = "medicalDebt"
    OTHER_DEBT = "otherDebt"


class Account(BaseModel):
    """Account information"""
    id: str
    name: str
    type: AccountType
    on_budget: bool
    closed: bool
    note: Optional[str] = None
    balance: int  # In milliunits
    cleared_balance: int  # In milliunits
    uncleared_balance: int  # In milliunits
    transfer_payee_id: Optional[str] = None
    direct_import_linked: Optional[bool] = False
    direct_import_in_error: Optional[bool] = False
    last_reconciled_at: Optional[str] = None  # ISO date string
    deleted: bool = False
    
    @computed_field
    @property
    def balance_formatted(self) -> float:
        """Return balance in standard currency format (dollars/euros)"""
        return self.balance / 1000.0
    
    @computed_field
    @property
    def cleared_balance_formatted(self) -> float:
        """Return cleared balance in standard currency format"""
        return self.cleared_balance / 1000.0
    
    @computed_field
    @property
    def uncleared_balance_formatted(self) -> float:
        """Return uncleared balance in standard currency format"""
        return self.uncleared_balance / 1000.0