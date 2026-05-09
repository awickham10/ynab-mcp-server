"""Budget setup prompt."""

from fastmcp.prompts import prompt


@prompt(name="budget_setup")
async def budget_setup_prompt(budget_id: str = "last-used") -> str:
    """Generate a prompt for budget setup and optimization guidance.

    Args:
        budget_id: The ID of the budget to analyze.
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
