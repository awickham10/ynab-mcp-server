"""
Custom exceptions for YNAB MCP Server
"""


class YNABMCPException(Exception):
    """Base exception for YNAB MCP Server"""
    pass


class YNABAPIException(YNABMCPException):
    """Exception raised when YNAB API returns an error"""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AuthenticationException(YNABMCPException):
    """Exception raised for authentication errors"""
    pass


class RateLimitException(YNABAPIException):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class BudgetNotFoundException(YNABAPIException):
    """Exception raised when a budget is not found"""
    
    def __init__(self, budget_id: str):
        super().__init__(f"Budget with ID '{budget_id}' not found", status_code=404)
        self.budget_id = budget_id


class AccountNotFoundException(YNABAPIException):
    """Exception raised when an account is not found"""
    
    def __init__(self, account_id: str):
        super().__init__(f"Account with ID '{account_id}' not found", status_code=404)
        self.account_id = account_id


class PayeeNotFoundException(YNABAPIException):
    """Exception raised when a payee is not found"""
    
    def __init__(self, payee_id: str):
        super().__init__(f"Payee with ID '{payee_id}' not found", status_code=404)
        self.payee_id = payee_id


class InvalidDateException(YNABMCPException):
    """Exception raised for invalid date formats"""
    
    def __init__(self, date_str: str):
        super().__init__(f"Invalid date format: '{date_str}'. Expected format: YYYY-MM-DD")
        self.date_str = date_str