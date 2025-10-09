"""
MCP Tools for YNAB integration
"""

from datetime import datetime
from typing import Optional, List, Tuple
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from .services import YNABService
from .exceptions import YNABAPIException, BudgetNotFoundException, AccountNotFoundException, PayeeNotFoundException, CategoryNotFoundException
from .resources import (
    TRANSACTIONS_WIDGET_ID,
    TRANSACTION_DETAIL_WIDGET_ID,
    widget_embedded_resource_json,
    widget_meta_base,
)


def _is_memo_empty(memo: Optional[str]) -> bool:
    """Check if a memo is empty or blank (None, empty string, or only whitespace)"""
    return memo is None or memo.strip() == ""


def register_tools(mcp: FastMCP) -> None:
    """Register all YNAB tools with the MCP server"""
    
    # Keep track of registered tools for logging
    registered_tools = []
    
    @mcp.tool(
        name="get_budgets",
        tags={"budget", "overview", "readonly"},
        annotations={
            "title": "Get All Budgets", 
            "readOnlyHint": True,
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "budget-info"}
    )
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
    
    @mcp.tool(
        name="get_budget", 
        tags={"budget", "details", "readonly"},
        annotations={
            "title": "Get Budget Details",
            "readOnlyHint": True, 
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "budget-info"}
    )
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
    
    @mcp.tool(
        name="get_accounts",
        tags={"accounts", "balances", "readonly"},
        annotations={
            "title": "Get All Accounts",
            "readOnlyHint": True,
            "openWorldHint": True  
        },
        meta={"version": "1.0", "category": "account-info"}
    )
    async def get_accounts(budget_id: str = "last-used") -> dict:
        """Get all accounts for a specific budget including balances and account types
        
        Returns checking, savings, credit cards, and other account information.
        Use this to see account balances, account names, or when you need account IDs
        for filtering transactions by account.
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing all accounts with names, balances, and account details
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
    
    @mcp.tool(
        name="get_account",
        tags={"accounts", "details", "readonly"}, 
        annotations={
            "title": "Get Account Details",
            "readOnlyHint": True,
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "account-info"}
    )
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
    
    @mcp.tool(
        name="get_transactions",
        tags={"transactions", "readonly", "data-cleanup"},
        annotations={
            "title": "Get Transactions",
            "readOnlyHint": True,
            "openWorldHint": True
        },
        meta={
            "version": "1.1",
            "category": "transaction-data",
            "supports_compound_filtering": True,
            # Widget / template metadata for OpenAI Apps SDK style rendering
            **widget_meta_base(TRANSACTIONS_WIDGET_ID),
            "openai.com/widget": widget_embedded_resource_json(TRANSACTIONS_WIDGET_ID),
        }
    )
    async def get_transactions(
        budget_id: str = "last-used", 
        account_id: Optional[str] = None,
        payee_id: Optional[List[str] | str] = None,
        category_id: Optional[str] = None,
        since_date: Optional[str] = None,
        transaction_type: Optional[str] = None,
        empty_memo: Optional[bool] = None,
        widget: bool = True
    ) -> dict:
        """Get transactions for a specific budget with smart compound filtering
        
        Supports multiple filter combinations and automatically chooses the most efficient
        API endpoint to minimize data transfer, then applies additional filters in-memory.
        
        Filter Priority (for optimal performance):
        1. Account + any other filters → Uses account endpoint, filters rest in-memory
        2. Category + Payee → Uses category endpoint, filters payee in-memory  
        3. Category only → Uses category endpoint
        4. Payee only → Uses payee endpoint
        5. No filters → Uses general transactions endpoint
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
            account_id: Optional account ID to filter transactions for a specific account
            payee_id: Optional payee ID or list of payee IDs to filter transactions for specific payees
            category_id: Optional category ID to filter transactions for a specific category
            since_date: Optional date to filter transactions (format: YYYY-MM-DD)
            transaction_type: Optional transaction type filter ('uncategorized' or 'unapproved')
            empty_memo: Optional boolean to find transactions missing memos for data cleanup. 
                       Use True to find transactions with blank/empty memos that need descriptions added.
                       Use False to find transactions that already have memo text.
                       Useful for identifying transactions needing additional details or categorization.
        
        Returns:
            Dictionary containing transaction information with applied filters
        """
        try:
            # Get the authenticated user's access token
            token = get_access_token()
            if not token:
                return {"error": "No valid authentication token found"}
            
            access_token = token.token
            service = YNABService(access_token)
            
            # Handle JSON string payee_id parameter
            # If payee_id is a string that looks like a JSON array, parse it
            if payee_id and isinstance(payee_id, str) and payee_id.strip().startswith('['):
                try:
                    import json
                    payee_id = json.loads(payee_id)
                except (json.JSONDecodeError, ValueError):
                    # If parsing fails, treat as a single payee ID string
                    pass
            
            # Smart endpoint selection to minimize data transfer
            # Priority: account > category > payee > all transactions
            
            if account_id:
                # Account transactions are typically the narrowest scope
                # Use account endpoint and filter by payee/category in code
                transactions = await service.get_transactions(
                    budget_id, 
                    account_id=account_id,
                    since_date=since_date,
                    transaction_type=transaction_type
                )
                
                # Apply additional filters in-memory
                filtered_transactions = transactions
                if payee_id:
                    if isinstance(payee_id, list):
                        filtered_transactions = [t for t in filtered_transactions if t.payee_id in payee_id]
                    else:
                        filtered_transactions = [t for t in filtered_transactions if t.payee_id == payee_id]
                if category_id:
                    filtered_transactions = [t for t in filtered_transactions if t.category_id == category_id]
                if empty_memo is not None:
                    if empty_memo:
                        filtered_transactions = [t for t in filtered_transactions if _is_memo_empty(t.memo)]
                    else:
                        filtered_transactions = [t for t in filtered_transactions if not _is_memo_empty(t.memo)]
                
                tx_models = [transaction.model_dump() for transaction in filtered_transactions]
                response = {
                    "transactions": tx_models,
                    "count": len(filtered_transactions),
                    "account_id": account_id,
                    "budget_id": budget_id
                }
                if payee_id:
                    response["payee_id"] = payee_id
                if category_id:
                    response["category_id"] = category_id
                if empty_memo is not None:
                    response["empty_memo"] = empty_memo
                if widget:
                    structured_content, meta = _build_transactions_widget_payload(tx_models)
                    response["structuredContent"] = structured_content
                    response.setdefault("_meta", {}).update(meta)
                    
                return response
                
            elif category_id and payee_id:
                # Both category and payee specified (no account)
                # Categories are typically more focused than payees, so use category endpoint
                transactions = await service.get_category_transactions(
                    budget_id, 
                    category_id,
                    since_date=since_date,
                    transaction_type=transaction_type
                )
                
                # Filter by payee and memo in-memory
                if isinstance(payee_id, list):
                    filtered_transactions = [t for t in transactions if t.payee_id in payee_id]
                else:
                    filtered_transactions = [t for t in transactions if t.payee_id == payee_id]
                if empty_memo is not None:
                    if empty_memo:
                        filtered_transactions = [t for t in filtered_transactions if _is_memo_empty(t.memo)]
                    else:
                        filtered_transactions = [t for t in filtered_transactions if not _is_memo_empty(t.memo)]
                
                tx_models = [transaction.model_dump() for transaction in filtered_transactions]
                response = {
                    "transactions": tx_models,
                    "count": len(filtered_transactions),
                    "category_id": category_id,
                    "payee_id": payee_id,
                    "budget_id": budget_id,
                    "filtered_by": "category_then_payee"
                }
                if empty_memo is not None:
                    response["empty_memo"] = empty_memo
                if widget:
                    structured_content, meta = _build_transactions_widget_payload(tx_models)
                    response["structuredContent"] = structured_content
                    response.setdefault("_meta", {}).update(meta)
                
                return response
                
            elif category_id:
                # Only category specified, use category endpoint
                transactions = await service.get_category_transactions(
                    budget_id, 
                    category_id,
                    since_date=since_date,
                    transaction_type=transaction_type
                )
                
                # Apply memo filter if specified
                filtered_transactions = transactions
                if empty_memo is not None:
                    if empty_memo:
                        filtered_transactions = [t for t in filtered_transactions if _is_memo_empty(t.memo)]
                    else:
                        filtered_transactions = [t for t in filtered_transactions if not _is_memo_empty(t.memo)]
                
                tx_models = [transaction.model_dump() for transaction in filtered_transactions]
                response = {
                    "transactions": tx_models,
                    "count": len(filtered_transactions),
                    "category_id": category_id,
                    "budget_id": budget_id
                }
                if empty_memo is not None:
                    response["empty_memo"] = empty_memo
                if widget:
                    structured_content, meta = _build_transactions_widget_payload(tx_models)
                    response["structuredContent"] = structured_content
                    response.setdefault("_meta", {}).update(meta)
                
                return response
                
            elif payee_id:
                # Payee specified (single or multiple)
                if isinstance(payee_id, list):
                    # Multiple payees - call get_payee_transactions for each payee
                    filtered_transactions = []
                    for single_payee_id in payee_id:
                        payee_transactions = await service.get_payee_transactions(
                            budget_id, 
                            single_payee_id,
                            since_date=since_date,
                            transaction_type=transaction_type
                        )
                        filtered_transactions.extend(payee_transactions)
                else:
                    # Single payee - use optimized payee endpoint
                    filtered_transactions = await service.get_payee_transactions(
                        budget_id, 
                        payee_id,
                        since_date=since_date,
                        transaction_type=transaction_type
                    )
                
                # Apply memo filter if specified
                if empty_memo is not None:
                    if empty_memo:
                        filtered_transactions = [t for t in filtered_transactions if _is_memo_empty(t.memo)]
                    else:
                        filtered_transactions = [t for t in filtered_transactions if not _is_memo_empty(t.memo)]
                
                tx_models = [transaction.model_dump() for transaction in filtered_transactions]
                response = {
                    "transactions": tx_models,
                    "count": len(filtered_transactions),
                    "payee_id": payee_id,
                    "budget_id": budget_id
                }
                if empty_memo is not None:
                    response["empty_memo"] = empty_memo
                if widget:
                    structured_content, meta = _build_transactions_widget_payload(tx_models)
                    response["structuredContent"] = structured_content
                    response.setdefault("_meta", {}).update(meta)
                
                return response
            else:
                # No specific filters, get all transactions
                transactions = await service.get_transactions(
                    budget_id, 
                    since_date=since_date,
                    transaction_type=transaction_type
                )
                
                # Apply memo filter if specified
                filtered_transactions = transactions
                if empty_memo is not None:
                    if empty_memo:
                        filtered_transactions = [t for t in filtered_transactions if _is_memo_empty(t.memo)]
                    else:
                        filtered_transactions = [t for t in filtered_transactions if not _is_memo_empty(t.memo)]
                
                tx_models = [transaction.model_dump() for transaction in filtered_transactions]
                response = {
                    "transactions": tx_models,
                    "count": len(filtered_transactions),
                    "budget_id": budget_id
                }
                if empty_memo is not None:
                    response["empty_memo"] = empty_memo
                if widget:
                    structured_content, meta = _build_transactions_widget_payload(tx_models)
                    response["structuredContent"] = structured_content
                    response.setdefault("_meta", {}).update(meta)
                
                return response
        except BudgetNotFoundException as e:
            return {"error": str(e), "budget_id": e.budget_id}
        except AccountNotFoundException as e:
            return {"error": str(e), "account_id": e.account_id}
        except PayeeNotFoundException as e:
            return {"error": str(e), "payee_id": e.payee_id}
        except CategoryNotFoundException as e:
            return {"error": str(e), "category_id": e.category_id}
        except YNABAPIException as e:
            return {"error": str(e), "status_code": e.status_code}

    def _build_transactions_widget_payload(transactions: List[dict]) -> Tuple[dict, dict]:
        """Build structured content and metadata for the transactions widget."""

        limit = 6
        total_count = len(transactions)

        def format_amount(milliunits: int | None) -> str:
            if milliunits is None:
                return ""
            major = milliunits / 1000.0
            if major < 0:
                return f"-${abs(major):,.2f}"
            return f"${major:,.2f}"

        def format_date(value: Optional[str]) -> str:
            if not value:
                return "—"
            try:
                parsed = datetime.strptime(value, "%Y-%m-%d")
                return parsed.strftime("%b %d").replace(" 0", " ")
            except ValueError:
                return value

        def clean_memo(memo: Optional[str]) -> Optional[str]:
            if memo is None:
                return None
            text = memo.strip()
            if not text:
                return None
            return text if len(text) <= 40 else f"{text[:37]}…"

        outflow_total = sum((t.get("amount") or 0) for t in transactions if (t.get("amount") or 0) < 0)
        inflow_total = sum((t.get("amount") or 0) for t in transactions if (t.get("amount") or 0) > 0)
        net_total = outflow_total + inflow_total

        rows: List[dict] = []
        for idx, transaction in enumerate(transactions[:limit]):
            amount = transaction.get("amount")
            amount_color = "danger" if amount is not None and amount < 0 else "success" if amount and amount > 0 else "secondary"
            rows.append(
                {
                    "id": transaction.get("id") or f"row-{idx}",
                    "payee": transaction.get("payee_name") or transaction.get("account_name") or "Unknown payee",
                    "amount": format_amount(amount),
                    "amountColor": amount_color,
                    "date": format_date(transaction.get("date")),
                    "category": transaction.get("category_name") or "Uncategorized",
                    "needsApproval": not bool(transaction.get("approved", True)),
                    "memo": clean_memo(transaction.get("memo")),
                }
            )

        display_count = len(rows)
        if total_count == 0:
            subtitle = "No transactions found"
        elif total_count > display_count:
            subtitle = f"Showing {display_count} of {total_count} transactions"
        else:
            plural = "transaction" if display_count == 1 else "transactions"
            subtitle = f"{display_count} {plural}"

        summary = {
            "title": "Recent transactions",
            "subtitle": subtitle,
            "rowCount": total_count,
            "displayCount": display_count,
            "outflow": format_amount(outflow_total if outflow_total else 0),
            "inflow": format_amount(inflow_total if inflow_total else 0),
            "net": format_amount(net_total),
            "netColor": "danger" if net_total < 0 else "success" if net_total > 0 else "secondary",
        }

        structured_content = {
            "summary": summary,
            "rows": rows,
        }

        meta = widget_meta_base(TRANSACTIONS_WIDGET_ID)
        meta["openai.com/widget"] = widget_embedded_resource_json(TRANSACTIONS_WIDGET_ID)
        meta["widget"] = {
            "design_spec": "Compact card summarizing recent YNAB transactions with totals and review states.",
            "complexity_budget": "Within budget: summary metrics and up to six list items.",
        }

        return structured_content, meta

    @mcp.tool(
        name="get_categories",
        tags={"categories", "budgeting", "readonly"},
        annotations={
            "title": "Get Budget Categories",
            "readOnlyHint": True,
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "category-info"}
    )
    async def get_categories(budget_id: str = "last-used") -> dict:
        """Get all categories and category groups for a specific budget
        
        Returns both category groups (like "Food", "Transportation") and individual categories 
        (like "Groceries", "Gas"). Use this when you need category IDs for filtering transactions
        or when users ask about their budget categories and spending limits.
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing all categories organized by category groups with budgeted amounts
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
    
    @mcp.tool(
        name="get_payees", 
        tags={"payees", "merchants", "readonly"},
        annotations={
            "title": "Get All Payees",
            "readOnlyHint": True,
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "payee-info"}
    )
    async def get_payees(budget_id: str = "last-used") -> dict:
        """Get all payees (merchants, people, places) for a specific budget
        
        Returns all entities that have been paid money to or received money from.
        Use this when you need payee IDs for filtering transactions, or when users
        want to see all the places they spend money (restaurants, stores, etc.).
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing all payees with their names and IDs
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
    
    @mcp.tool(
        name="find_payee_by_name",
        tags={"payees", "search", "readonly"},
        annotations={
            "title": "Find Payee by Name",
            "readOnlyHint": True,
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "payee-search", "search_type": "partial_match"}
    )
    async def find_payee_by_name(
        payee_name: str,
        budget_id: str = "last-used"
    ) -> dict:
        """Find payees by name using case-insensitive partial matching
        
        Use this when you need to search for payees without knowing their exact name or ID.
        Particularly useful for finding payees when users provide partial names, common names,
        or slight variations of business names (e.g., "Starbucks", "starbucks", "Star").
        
        Args:
            payee_name: The name or partial name of the payee to search for (case-insensitive)
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
        
        Returns:
            Dictionary containing all payees whose names contain the search term
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
    
    @mcp.tool(
        name="analyze_spending",
        tags={"analytics", "spending", "insights", "readonly"},
        annotations={
            "title": "Analyze Spending Patterns",
            "readOnlyHint": True,
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "analytics", "analysis_type": "spending_trends"}
    )
    async def analyze_spending(budget_id: str = "last-used", months: int = 3) -> dict:
        """Analyze spending patterns and trends for a budget over a specified time period
        
        Provides insights into spending habits including total spending, top categories,
        transaction counts, and daily averages. Use this when users want to understand
        their spending behavior, identify areas of high spending, or get budget insights.
        
        Args:
            budget_id: The ID of the budget (use 'last-used' for the most recent budget)
            months: Number of months to analyze going back from today (default: 3, max recommended: 12)
        
        Returns:
            Dictionary containing comprehensive spending analysis with formatted amounts and trends
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
    
    @mcp.tool(
        name="update_transaction",
        tags={"transactions", "editing", "modify"},
        annotations={
            "title": "Update Transaction Details",
            "readOnlyHint": False,
            "destructiveHint": False,  # Non-destructive modification
            "idempotentHint": True,    # Same update calls produce same result
            "openWorldHint": True
        },
        meta={"version": "1.0", "category": "transaction-editing", "modifies_data": True}
    )
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
        """Update an existing transaction with new details
        
        Use this to modify transaction information like adding memos, changing amounts,
        updating categories, or marking transactions as cleared. All parameters are optional
        - only provide the fields you want to update.
        
        Args:
            budget_id: The ID of the budget
            transaction_id: The ID of the transaction to update
            memo: Transaction memo/description (max 500 characters). Use to add context or notes.
            amount: Amount in standard currency format (e.g., 50.00 for $50.00, -25.99 for expenses)
            payee_id: Payee ID (use get_payees or find_payee_by_name to find valid IDs)
            payee_name: Payee name (alternative to payee_id, will create payee if doesn't exist)
            category_id: Category ID (use get_categories to find valid IDs)
            cleared: Cleared status - 'cleared' (reconciled with bank), 'uncleared' (pending), 'reconciled' (final)
            approved: Whether transaction is approved (False for transactions needing review)
            flag_color: Visual flag color for organization ('red', 'orange', 'yellow', 'green', 'blue', 'purple')
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