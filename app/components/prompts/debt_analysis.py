"""Debt analysis prompt."""

from fastmcp.prompts import prompt


@prompt(name="debt_analysis")
async def debt_analysis_prompt(budget_id: str = "last-used") -> str:
    """Generate a prompt for debt analysis and payoff strategy.

    Args:
        budget_id: The ID of the budget to analyze.
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
