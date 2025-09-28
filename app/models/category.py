"""
Category-related models
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, computed_field


class GoalType(str, Enum):
    """Category goal types"""
    TB = "TB"      # Target Category Balance
    TBD = "TBD"    # Target Category Balance by Date
    MF = "MF"      # Monthly Funding
    NEED = "NEED"  # Plan Your Spending
    DEBT = "DEBT"  # Debt goal


class CategoryGroup(BaseModel):
    """Category group information"""
    id: str
    name: str
    hidden: bool
    deleted: bool = False


class Category(BaseModel):
    """Category information"""
    id: str
    category_group_id: str
    category_group_name: Optional[str] = None
    name: str
    hidden: bool
    note: Optional[str] = None
    budgeted: int  # In milliunits
    activity: int  # In milliunits  
    balance: int  # In milliunits
    goal_type: Optional[GoalType] = None
    goal_needs_whole_amount: Optional[bool] = None
    goal_day: Optional[int] = None
    goal_cadence: Optional[int] = None
    goal_cadence_frequency: Optional[int] = None
    goal_creation_month: Optional[str] = None  # ISO date YYYY-MM-DD
    goal_target: Optional[int] = None  # In milliunits
    goal_target_month: Optional[str] = None  # ISO date YYYY-MM-DD
    goal_percentage_complete: Optional[int] = None
    goal_months_to_budget: Optional[int] = None
    goal_under_funded: Optional[int] = None  # In milliunits
    goal_overall_funded: Optional[int] = None  # In milliunits
    goal_overall_left: Optional[int] = None  # In milliunits
    deleted: bool = False
    
    @computed_field
    @property
    def budgeted_formatted(self) -> float:
        """Return budgeted amount in standard currency format"""
        return self.budgeted / 1000.0
    
    @computed_field
    @property
    def activity_formatted(self) -> float:
        """Return activity amount in standard currency format"""
        return self.activity / 1000.0
    
    @computed_field
    @property
    def balance_formatted(self) -> float:
        """Return balance in standard currency format"""
        return self.balance / 1000.0
    
    @computed_field
    @property
    def goal_target_formatted(self) -> Optional[float]:
        """Return goal target in standard currency format"""
        return self.goal_target / 1000.0 if self.goal_target is not None else None
    
    @computed_field
    @property
    def goal_under_funded_formatted(self) -> Optional[float]:
        """Return goal under funded amount in standard currency format"""
        return self.goal_under_funded / 1000.0 if self.goal_under_funded is not None else None
    
    @computed_field
    @property
    def goal_overall_funded_formatted(self) -> Optional[float]:
        """Return goal overall funded amount in standard currency format"""
        return self.goal_overall_funded / 1000.0 if self.goal_overall_funded is not None else None
    
    @computed_field
    @property
    def goal_overall_left_formatted(self) -> Optional[float]:
        """Return goal overall left amount in standard currency format"""
        return self.goal_overall_left / 1000.0 if self.goal_overall_left is not None else None