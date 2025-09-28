"""
MCP Tools for YNAB integration
"""

from typing import Optional, List
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from ..services import YNABService
from ..exceptions import YNABAPIException, BudgetNotFoundException, AccountNotFoundException, PayeeNotFoundException


def register_tools(mcp: FastMCP) -> None:
    """Register all YNAB tools with the MCP server"""
    
    # Keep track of registered tools for logging
    registered_tools = []
    
    @mcp.tool
    async def get_budgets(include_accounts: bool = False) -> dict:
        """Get all budgets for the authenticated user
        
        Args:
            include_accounts: Whether to include account summaries in the response
        
        Returns:
            Dictionary containing budget summaries
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            budgets = await service.get_budgets(include_accounts=include_accounts)
            return {
                "budgets": [budget.model_dump() for budget in budgets],
                "count": len(budgets)
            }
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def get_budget(budget_id: str = "last-used") -> dict:
        """Get detailed information for a specific budget
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing detailed budget information
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            budget = await service.get_budget(budget_id)
            return budget.model_dump()
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def get_accounts(budget_id: str = "last-used") -> dict:
        """Get all accounts for a specific budget
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing account information
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            accounts = await service.get_accounts(budget_id)
            return {
                "accounts": [account.model_dump() for account in accounts],
                "count": len(accounts)
            }
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def get_account(budget_id: str, account_id: str) -> dict:
        """Get information for a specific account
        
        Args:
            budget_id: The ID of the budget
            account_id: The ID of the account
        
        Returns:
            Dictionary containing account information
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            account = await service.get_account(budget_id, account_id)
            return account.model_dump()
        except (BudgetNotFoundException, AccountNotFoundException) as e:
            return {"error": str(e)}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def get_transactions(
        budget_id: str = "last-used", 
        account_id: Optional[str] = None,
        payee_id: Optional[str] = None,
        since_date: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> dict:
        """Get transactions for a specific budget
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
            account_id: Optional account ID to filter transactions for a specific account
            payee_id: Optional payee ID to filter transactions for a specific payee
            since_date: Optional date to filter transactions (format: YYYY-MM-DD)
            transaction_type: Optional transaction type filter ('uncategorized' or 'unapproved')
        
        Returns:
            Dictionary containing transaction information
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            
            # If payee_id is provided, use the payee transactions endpoint
            if payee_id:
                transactions = await service.get_payee_transactions(
                    budget_id, 
                    payee_id,
                    since_date=since_date,
                    transaction_type=transaction_type
                )
                return {
                    "transactions": [transaction.model_dump() for transaction in transactions],
                    "count": len(transactions),
                    "payee_id": payee_id,
                    "budget_id": budget_id
                }
            else:
                # Use the regular transactions endpoint
                transactions = await service.get_transactions(
                    budget_id, 
                    account_id=account_id,
                    since_date=since_date,
                    transaction_type=transaction_type
                )
                return {
                    "transactions": [transaction.model_dump() for transaction in transactions],
                    "count": len(transactions),
                    "account_id": account_id  # Include account_id in response for clarity
                }
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except AccountNotFoundException as e:
            return {"error": str(e), "account_id": e.account_id}
        except PayeeNotFoundException as e:
            return {"error": str(e), "payee_id": e.payee_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def get_categories(budget_id: str = "last-used") -> dict:
        """Get all categories for a specific budget
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing category information
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            categories = await service.get_categories(budget_id)
            return {
                "categories": [category.model_dump() for category in categories],
                "count": len(categories)
            }
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def get_payees(budget_id: str = "last-used") -> dict:
        """Get all payees for a specific budget
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing payee information
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            payees = await service.get_payees(budget_id)
            return {
                "payees": [payee.model_dump() for payee in payees],
                "count": len(payees)
            }
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def find_payee_by_name(
        payee_name: str,
        budget_id: str = "last-used"
    ) -> dict:
        """Find payees by name (case-insensitive partial matching)
        
        Args:
            payee_name: The name or partial name of the payee to search for
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing matching payees
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            all_payees = await service.get_payees(budget_id)
            
            # Search for payees with names containing the search term (case-insensitive)
            search_term = payee_name.lower().strip()
            matching_payees = [
                payee for payee in all_payees 
                if payee.name and search_term in payee.name.lower()
            ]
            
            return {
                "payees": [payee.model_dump() for payee in matching_payees],
                "count": len(matching_payees),
                "search_term": payee_name,
                "budget_id": budget_id
            }
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool 
    async def analyze_spending(budget_id: str = "last-used", months: int = 3) -> dict:
        """Analyze spending patterns for a budget
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
            months: Number of months to analyze (default: 3)
        
        Returns:
            Dictionary containing spending analysis
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            
            # Get recent transactions for analysis
            from datetime import datetime, timedelta
            since_date = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")
            transactions = await service.get_transactions(budget_id, since_date=since_date)
            categories = await service.get_categories(budget_id)
            
            # Basic spending analysis
            total_spending = sum(t.amount for t in transactions if t.amount < 0)  # Negative amounts are expenses
            category_spending = {}
            
            for transaction in transactions:
                if transaction.amount < 0 and transaction.category_name:
                    category_name = transaction.category_name
                    if category_name not in category_spending:
                        category_spending[category_name] = 0
                    category_spending[category_name] += abs(transaction.amount)
            
            # Sort categories by spending
            top_spending_categories = sorted(
                category_spending.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            return {
                "analysis_period_days": 30 * months,
                "total_spending_milliunits": abs(total_spending),
                "total_spending_formatted": abs(total_spending) / 1000.0,
                "transaction_count": len([t for t in transactions if t.amount < 0]),
                "top_spending_categories": [
                    {
                        "category": cat,
                        "amount_milliunits": amount,
                        "amount_formatted": amount / 1000.0
                    }
                    for cat, amount in top_spending_categories
                ],
                "average_daily_spending": abs(total_spending) / (30 * months) / 1000.0 if total_spending else 0
            }
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}
    
    @mcp.tool
    async def update_transaction(
        budget_id: str,
        transaction_id: str,
        memo: Optional[str] = None,
        amount: Optional[float] = None,
        payee_id: Optional[str] = None,
        payee_name: Optional[str] = None,
        category_id: Optional[str] = None,
        cleared: Optional[str] = None,
        approved: Optional[bool] = None,
        flag_color: Optional[str] = None,
        date: Optional[str] = None
    ) -> dict:
        """Update an existing transaction
        
        Args:
            budget_id: The ID of the budget
            transaction_id: The ID of the transaction to update
            memo: Transaction memo (max 500 characters)
            amount: Amount in standard currency format (e.g., 50.00 for $50.00)
            payee_id: Payee ID
            payee_name: Payee name (alternative to payee_id)
            category_id: Category ID
            cleared: Cleared status ('cleared', 'uncleared', 'reconciled')
            approved: Whether transaction is approved
            flag_color: Flag color ('red', 'orange', 'yellow', 'green', 'blue', 'purple')
            date: Transaction date in YYYY-MM-DD format
        
        Returns:
            Dictionary containing the updated transaction information
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            
            # Convert amount from standard format to milliunits if provided
            amount_milliunits = None
            if amount is not None:
                amount_milliunits = int(amount * 1000)
            
            # Validate cleared status if provided
            if cleared is not None and cleared not in ["cleared", "uncleared", "reconciled"]:
                return {"error": f"Invalid cleared status '{cleared}'. Must be one of: cleared, uncleared, reconciled"}
            
            # Validate flag color if provided
            if flag_color is not None and flag_color not in ["red", "orange", "yellow", "green", "blue", "purple"]:
                return {"error": f"Invalid flag color '{flag_color}'. Must be one of: red, orange, yellow, green, blue, purple"}
            
            transaction = await service.update_transaction(
                budget_id=budget_id,
                transaction_id=transaction_id,
                memo=memo,
                amount=amount_milliunits,
                payee_id=payee_id,
                payee_name=payee_name,
                category_id=category_id,
                cleared=cleared,
                approved=approved,
                flag_color=flag_color,
                date=date
            )
            
            return transaction.model_dump()
            
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}