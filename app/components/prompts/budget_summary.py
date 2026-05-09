"""Budget summary prompt."""

from fastmcp.prompts import prompt


@prompt(name="budget_summary")
async def budget_summary_prompt(budget_id: str = "last-used") -> str:
    """Generate a prompt for comprehensive budget summary analysis.

    Args:
        budget_id: The ID of the budget to analyze (defaults to 'last-used').
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
