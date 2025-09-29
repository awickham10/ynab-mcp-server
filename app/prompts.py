"""
MCP Prompts for YNAB integration
"""

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register all YNAB prompts with the MCP server"""
    
    @mcp.prompt("budget_summary")
    async def budget_summary_prompt(budget_id: str = "last-used") -> str:
        """Generate a prompt for comprehensive budget summary analysis
        
        Args:
            budget_id: The ID of the budget to analyze (defaults to 'last-used')
        
        Returns:
            A detailed prompt for budget analysis
        """
        return f"""
Please analyze the YNAB budget with ID '{budget_id}' and provide a comprehensive summary.

Use the available YNAB tools to gather the following information and provide insights:

## Budget Overview
1. Get the basic budget information using get_budget
2. Summarize key budget metrics and settings

## Account Analysis  
1. Use get_accounts to retrieve all accounts
2. Analyze account balances (checking, savings, credit cards, etc.)
3. Identify accounts that may need attention (low balances, high credit card balances)

## Spending Analysis
1. Use get_transactions to get recent transactions (last 30-90 days)
2. Use analyze_spending to get spending patterns
3. Identify top spending categories
4. Calculate average daily/monthly spending

## Category Performance
1. Use get_categories to get all budget categories
2. Analyze which categories are over/under budget
3. Identify categories with goals and their progress
4. Look for categories that consistently go over budget

## Financial Health Assessment
Based on the data gathered, provide:
1. Overall budget health score (1-10)
2. Areas of concern or overspending
3. Positive trends and good habits
4. Specific recommendations for improvement
5. Suggested budget adjustments

## Action Items
Provide 3-5 specific, actionable recommendations such as:
- Adjusting category budget amounts
- Setting up new goals or targets
- Account management suggestions
- Spending behavior changes

Format the analysis in a clear, easy-to-read structure with sections and bullet points.
Include specific dollar amounts and percentages where relevant.
"""

    @mcp.prompt("spending_analysis")
    async def spending_analysis_prompt(budget_id: str = "last-used", category_name: str = "", months: int = 3) -> str:
        """Generate a prompt for detailed spending analysis
        
        Args:
            budget_id: The ID of the budget to analyze
            category_name: Specific category to focus on (optional)
            months: Number of months to analyze (default: 3)
        
        Returns:
            A prompt for detailed spending analysis
        """
        category_focus = f"with special attention to the '{category_name}' category" if category_name else ""
        
        return f"""
Please perform a detailed spending analysis for YNAB budget '{budget_id}' over the last {months} months {category_focus}.

## Data Collection
1. Use get_transactions to retrieve transactions for the last {months * 30} days
2. Use analyze_spending to get automated analysis for {months} months
3. Use get_categories to understand budget allocations

## Analysis Requirements

### Spending Trends
- Monthly spending totals and trends
- Week-over-week and month-over-month changes
- Seasonal patterns or anomalies

### Category Breakdown
- Top 10 spending categories by amount
- Categories that exceeded their budget
- Categories with unusual activity
{"- Deep dive into '" + category_name + "' category spending patterns" if category_name else ""}

### Transaction Patterns
- Average transaction size by category
- Frequency of spending by category
- Largest individual transactions
- Recurring vs. one-time expenses

### Budget Performance
- Percentage of budget used by category
- Categories consistently over/under budget
- Goal progress for categories with targets

## Insights & Recommendations
Provide specific insights such as:
1. Which spending habits are serving the budget well
2. Problem areas that need immediate attention
3. Optimization opportunities (reallocating budget between categories)
4. Suggested spending limits or goals
5. Behavioral changes that could improve financial health

Format with clear headings, bullet points, and include specific dollar amounts and percentages.
"""

    @mcp.prompt("budget_setup")
    async def budget_setup_prompt(budget_id: str = "last-used") -> str:
        """Generate a prompt for budget setup and optimization guidance
        
        Args:
            budget_id: The ID of the budget to analyze
        
        Returns:
            A prompt for budget setup guidance
        """
        return f"""
Please analyze YNAB budget '{budget_id}' and provide comprehensive setup and optimization guidance.

## Current State Analysis
1. Use get_budget to understand the current budget structure
2. Use get_accounts to review account setup
3. Use get_categories to analyze category organization
4. Use get_transactions to understand spending patterns

## Budget Structure Review
Analyze and provide recommendations for:

### Account Organization
- Are accounts properly categorized (on-budget vs. off-budget)?
- Are there accounts that should be added or removed?
- Is account naming clear and consistent?

### Category Structure
- Are categories well-organized and logical?
- Are there missing categories for current spending?
- Are there unused categories that should be removed?
- Should categories be grouped differently?

### Goal Setting
- Which categories would benefit from goals?
- Are current goals realistic and achievable?
- Should any goal types be changed (monthly funding vs. target balance)?

## Optimization Recommendations

### Budget Allocation
- Suggested budget amounts based on historical spending
- Categories that need budget increases/decreases
- Recommended emergency fund targets

### Workflow Improvements
- Account reconciliation recommendations
- Transaction categorization suggestions
- Payee setup for easier categorization

### Goal Strategy
- Priority order for funding different goals
- Timeline recommendations for major savings goals
- Debt payoff strategy if applicable

## Implementation Plan
Provide a step-by-step plan for implementing recommendations:
1. Immediate changes (this week)
2. Short-term improvements (this month)  
3. Long-term optimizations (next 3-6 months)

Include specific action items with dollar amounts and timelines where applicable.
"""

    @mcp.prompt("debt_analysis")
    async def debt_analysis_prompt(budget_id: str = "last-used") -> str:
        """Generate a prompt for debt analysis and payoff strategy
        
        Args:
            budget_id: The ID of the budget to analyze
        
        Returns:
            A prompt for debt analysis and payoff planning
        """
        return f"""
Please analyze the debt situation for YNAB budget '{budget_id}' and provide a comprehensive payoff strategy.

## Debt Discovery
1. Use get_accounts to identify all debt accounts (credit cards, loans, etc.)
2. Use get_transactions to analyze recent debt payments and charges
3. Use get_categories to see how debt payments are budgeted

## Debt Analysis
For each debt account, analyze:

### Account Details
- Current balance and account type
- Recent payment history
- New charges vs. payments trend

### Payment Strategy
- Current monthly payment amounts
- Minimum payment requirements (if available in transaction history)
- Interest costs (estimated from payment patterns)

## Payoff Strategy Development

### Debt Prioritization
Recommend payoff order considering:
- Balance amounts
- Estimated interest rates (based on payment patterns)
- Psychological factors (small vs. large balances)

### Payment Optimization
- Available budget for extra debt payments
- Snowball vs. avalanche method comparison
- Impact of different payment amounts on payoff timeline

### Budget Adjustments
- Categories that could be reduced to fund debt payments
- Opportunities to increase debt payment budgets
- Balancing debt payoff with other financial goals

## Action Plan
Provide a specific plan including:
1. Priority order for debt payoff
2. Recommended monthly payment amounts for each debt
3. Projected payoff timeline
4. Budget category adjustments needed
5. Milestone checkpoints and celebration goals

## Monitoring Strategy
Suggest how to track progress:
- Key metrics to monitor monthly
- Red flags that indicate strategy needs adjustment
- Success celebrations and motivation techniques

Include specific dollar amounts, timelines, and step-by-step instructions.
"""