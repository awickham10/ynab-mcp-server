"""
YNAB API service
"""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from ..config import config
from ..models import (
    Budget, BudgetSummary, Account, Transaction, TransactionDetail, 
    Category, CategoryGroup, Payee
)
from ..exceptions import (
    YNABAPIException, AuthenticationException, RateLimitException,
    BudgetNotFoundException, AccountNotFoundException, PayeeNotFoundException, InvalidDateException
)


class YNABService:
    """Service for interacting with YNAB API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = config.ynab_api_base_url
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to YNAB API"""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params or {},
                    json=json_data
                )
                
                if response.status_code == 401:
                    raise AuthenticationException("Invalid or expired access token")
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitException(retry_after=int(retry_after) if retry_after else None)
                elif response.status_code == 404:
                    error_data = response.json() if response.content else {}
                    raise YNABAPIException(
                        error_data.get("error", {}).get("detail", "Resource not found"),
                        status_code=404,
                        response_data=error_data
                    )
                elif not response.is_success:
                    error_data = response.json() if response.content else {}
                    raise YNABAPIException(
                        error_data.get("error", {}).get("detail", f"API error: {response.status_code}"),
                        status_code=response.status_code,
                        response_data=error_data
                    )
                
                return response.json()
                
            except httpx.RequestError as e:
                raise YNABAPIException(f"Network error: {str(e)}")
    
    def _validate_date_format(self, date_str: str) -> None:
        """Validate date string format"""
        if date_str:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise InvalidDateException(date_str)
    
    async def get_budgets(self, include_accounts: bool = False) -> List[BudgetSummary]:
        """Get all budgets for the authenticated user"""
        params = {"include_accounts": "true"} if include_accounts else {}
        response = await self._make_request("GET", "/budgets", params)
        
        budgets_data = response["data"]["budgets"]
        return [BudgetSummary(**budget) for budget in budgets_data]
    
    async def get_budget(self, budget_id: str, last_knowledge_of_server: Optional[int] = None) -> Budget:
        """Get detailed information for a specific budget"""
        params = {}
        if last_knowledge_of_server:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        
        try:
            response = await self._make_request("GET", f"/budgets/{budget_id}", params)
        except YNABAPIException as e:
            if e.status_code == 404:
                raise BudgetNotFoundException(budget_id)
            raise
        
        budget_data = response["data"]["budget"]
        return Budget(**budget_data, server_knowledge=response["data"]["server_knowledge"])
    
    async def get_accounts(self, budget_id: str, last_knowledge_of_server: Optional[int] = None) -> List[Account]:
        """Get all accounts for a specific budget"""
        params = {}
        if last_knowledge_of_server:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        
        try:
            response = await self._make_request("GET", f"/budgets/{budget_id}/accounts", params)
        except YNABAPIException as e:
            if e.status_code == 404:
                raise BudgetNotFoundException(budget_id)
            raise
        
        accounts_data = response["data"]["accounts"]
        return [Account(**account) for account in accounts_data]
    
    async def get_account(self, budget_id: str, account_id: str) -> Account:
        """Get a specific account"""
        try:
            response = await self._make_request("GET", f"/budgets/{budget_id}/accounts/{account_id}")
        except YNABAPIException as e:
            if e.status_code == 404:
                if "budget" in str(e).lower():
                    raise BudgetNotFoundException(budget_id)
                else:
                    raise AccountNotFoundException(account_id)
            raise
        
        account_data = response["data"]["account"]
        return Account(**account_data)
    
    async def get_transactions(
        self, 
        budget_id: str, 
        account_id: Optional[str] = None,
        since_date: Optional[str] = None,
        transaction_type: Optional[str] = None,
        last_knowledge_of_server: Optional[int] = None
    ) -> List[TransactionDetail]:
        """Get transactions for a specific budget, optionally filtered by account
        
        Args:
            budget_id: The budget ID
            account_id: Optional account ID to filter transactions for a specific account
            since_date: Optional date filter (YYYY-MM-DD format)
            transaction_type: Optional transaction type filter ('uncategorized' or 'unapproved')
            last_knowledge_of_server: Optional server knowledge parameter
            
        Returns:
            List of transaction details
        """
        if since_date:
            self._validate_date_format(since_date)
        
        params = {}
        if since_date:
            params["since_date"] = since_date
        if transaction_type:
            params["type"] = transaction_type
        if last_knowledge_of_server:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        
        # Use account-specific endpoint if account_id is provided
        if account_id:
            endpoint = f"/budgets/{budget_id}/accounts/{account_id}/transactions"
        else:
            endpoint = f"/budgets/{budget_id}/transactions"
        
        try:
            response = await self._make_request("GET", endpoint, params)
        except YNABAPIException as e:
            if e.status_code == 404:
                if account_id:
                    raise AccountNotFoundException(account_id)
                else:
                    raise BudgetNotFoundException(budget_id)
            raise
        
        transactions_data = response["data"]["transactions"]
        return [TransactionDetail(**transaction) for transaction in transactions_data]
    
    async def get_categories(self, budget_id: str, last_knowledge_of_server: Optional[int] = None) -> List[Category]:
        """Get all categories for a specific budget"""
        params = {}
        if last_knowledge_of_server:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        
        try:
            response = await self._make_request("GET", f"/budgets/{budget_id}/categories", params)
        except YNABAPIException as e:
            if e.status_code == 404:
                raise BudgetNotFoundException(budget_id)
            raise
        
        # YNAB returns category groups with categories nested inside
        category_groups = response["data"]["category_groups"]
        categories = []
        for group in category_groups:
            for category in group.get("categories", []):
                category["category_group_name"] = group["name"]
                categories.append(Category(**category))
        
        return categories
    
    async def get_payees(self, budget_id: str, last_knowledge_of_server: Optional[int] = None) -> List[Payee]:
        """Get all payees for a specific budget"""
        params = {}
        if last_knowledge_of_server:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        
        try:
            response = await self._make_request("GET", f"/budgets/{budget_id}/payees", params)
        except YNABAPIException as e:
            if e.status_code == 404:
                raise BudgetNotFoundException(budget_id)
            raise
        
        payees_data = response["data"]["payees"]
        return [Payee(**payee) for payee in payees_data]
    
    async def get_payee_transactions(
        self, 
        budget_id: str, 
        payee_id: str,
        since_date: Optional[str] = None,
        transaction_type: Optional[str] = None,
        last_knowledge_of_server: Optional[int] = None
    ) -> List[TransactionDetail]:
        """Get all transactions for a specific payee in a budget
        
        Args:
            budget_id: The budget ID
            payee_id: The payee ID
            since_date: Optional date filter (YYYY-MM-DD format)
            transaction_type: Optional transaction type filter ('uncategorized' or 'unapproved')
            last_knowledge_of_server: Optional server knowledge parameter
            
        Returns:
            List of transaction details for the specified payee
        """
        if since_date:
            self._validate_date_format(since_date)
        
        params = {}
        if since_date:
            params["since_date"] = since_date
        if transaction_type:
            params["type"] = transaction_type
        if last_knowledge_of_server:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        
        endpoint = f"/budgets/{budget_id}/payees/{payee_id}/transactions"
        
        try:
            response = await self._make_request("GET", endpoint, params)
        except YNABAPIException as e:
            if e.status_code == 404:
                # Check if it's budget not found or payee not found
                # YNAB API will return different error messages for budget vs payee not found
                if "budget" in str(e).lower():
                    raise BudgetNotFoundException(budget_id)
                else:
                    raise PayeeNotFoundException(payee_id)
            raise
        
        transactions_data = response["data"]["transactions"]
        return [TransactionDetail(**transaction) for transaction in transactions_data]
    
    async def update_transaction(
        self, 
        budget_id: str, 
        transaction_id: str,
        memo: Optional[str] = None,
        amount: Optional[int] = None,
        payee_id: Optional[str] = None,
        payee_name: Optional[str] = None,
        category_id: Optional[str] = None,
        cleared: Optional[str] = None,
        approved: Optional[bool] = None,
        flag_color: Optional[str] = None,
        date: Optional[str] = None
    ) -> TransactionDetail:
        """Update an existing transaction
        
        Args:
            budget_id: The budget ID
            transaction_id: The transaction ID to update
            memo: Transaction memo (max 500 characters)
            amount: Amount in milliunits (e.g., 50000 for $50.00)
            payee_id: Payee ID
            payee_name: Payee name (alternative to payee_id)
            category_id: Category ID
            cleared: Cleared status ('cleared', 'uncleared', 'reconciled')
            approved: Whether transaction is approved
            flag_color: Flag color ('red', 'orange', 'yellow', 'green', 'blue', 'purple')
            date: Transaction date in YYYY-MM-DD format
        """
        if date:
            self._validate_date_format(date)
        
        # Build the transaction update payload
        transaction_data = {}
        if memo is not None:
            transaction_data["memo"] = memo
        if amount is not None:
            transaction_data["amount"] = amount
        if payee_id is not None:
            transaction_data["payee_id"] = payee_id
        if payee_name is not None:
            transaction_data["payee_name"] = payee_name
        if category_id is not None:
            transaction_data["category_id"] = category_id
        if cleared is not None:
            transaction_data["cleared"] = cleared
        if approved is not None:
            transaction_data["approved"] = approved
        if flag_color is not None:
            transaction_data["flag_color"] = flag_color
        if date is not None:
            transaction_data["date"] = date
        
        payload = {"transaction": transaction_data}
        
        try:
            response = await self._make_request(
                "PUT", 
                f"/budgets/{budget_id}/transactions/{transaction_id}", 
                json_data=payload
            )
        except YNABAPIException as e:
            if e.status_code == 404:
                if "budget" in str(e).lower():
                    raise BudgetNotFoundException(budget_id)
                else:
                    # Could be transaction not found, but we don't have a specific exception for this
                    raise
            raise
        
        transaction_data = response["data"]["transaction"]
        return TransactionDetail(**transaction_data)