"""Spending analysis prompt."""

from fastmcp.prompts import prompt


@prompt(name="spending_analysis")
async def spending_analysis_prompt(
    budget_id: str = "last-used",
    category_name: str = "",
    months: int = 3,
) -> str:
    """Generate a prompt for detailed spending analysis.

    Args:
        budget_id: The ID of the budget to analyze.
        category_name: Specific category to focus on (optional).
        months: Number of months to analyze (default: 3).
    """
    category_focus = (
        f"with special attention to the '{category_name}' category" if category_name else ""
    )
    deep_dive = (
        f"- Deep dive into '{category_name}' category spending patterns" if category_name else ""
    )

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
{deep_dive}

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
