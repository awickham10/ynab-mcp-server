"""
Transaction-related models
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, computed_field


class TransactionClearedStatus(str, Enum):
    """Transaction cleared status"""
    CLEARED = "cleared"
    UNCLEARED = "uncleared"
    RECONCILED = "reconciled"


class TransactionFlagColor(str, Enum):
    """Transaction flag colors"""
    RED = "red"
    ORANGE = "orange" 
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"


class SubTransaction(BaseModel):
    """Subtransaction for split transactions"""
    id: str
    transaction_id: str
    amount: int  # In milliunits
    memo: Optional[str] = None
    payee_id: Optional[str] = None
    payee_name: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    transfer_account_id: Optional[str] = None
    transfer_transaction_id: Optional[str] = None
    deleted: bool = False
    
    @computed_field
    @property
    def amount_formatted(self) -> float:
        """Return amount in standard currency format"""
        return self.amount / 1000.0


class Transaction(BaseModel):
    """Basic transaction information"""
    id: str
    date: str  # ISO date format YYYY-MM-DD
    amount: int  # In milliunits
    memo: Optional[str] = None
    cleared: TransactionClearedStatus
    approved: bool
    flag_color: Optional[TransactionFlagColor] = None
    flag_name: Optional[str] = None
    account_id: str
    payee_id: Optional[str] = None
    category_id: Optional[str] = None
    transfer_account_id: Optional[str] = None
    transfer_transaction_id: Optional[str] = None
    matched_transaction_id: Optional[str] = None
    import_id: Optional[str] = None
    import_payee_name: Optional[str] = None
    import_payee_name_original: Optional[str] = None
    deleted: bool = False
    
    @computed_field
    @property
    def amount_formatted(self) -> float:
        """Return amount in standard currency format"""
        return self.amount / 1000.0


class TransactionDetail(Transaction):
    """Detailed transaction with additional fields"""
    account_name: str
    payee_name: Optional[str] = None
    category_name: Optional[str] = None
    subtransactions: List[SubTransaction] = Field(default_factory=list)
    
    @property
    def is_split(self) -> bool:
        """Check if this is a split transaction"""
        return len(self.subtransactions) > 0