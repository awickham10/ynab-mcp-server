"""
Payee-related models
"""

from typing import Optional
from pydantic import BaseModel


class Payee(BaseModel):
    """Payee information"""
    id: str
    name: str
    transfer_account_id: Optional[str] = None
    deleted: bool = False
    
    @property
    def is_transfer_payee(self) -> bool:
        """Check if this is a transfer payee"""
        return self.transfer_account_id is not None