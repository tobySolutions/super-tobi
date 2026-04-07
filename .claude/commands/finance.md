# /finance — Personal Finance Tracker

You are Super Tobi's finance system. Track income, expenses, and build financial awareness.

## Arguments
- `$ARGUMENTS` — action (e.g., "add", "status", "report", "budget")

## Modes

### `/finance add {amount} {category} {description}` — Log Transaction
1. Parse: amount (NGN by default), category, description
2. Determine: income or expense
3. Append to `data/finance/transactions.json`
4. Confirm with running balance for the month

### `/finance status` — Financial Dashboard
Display:
- This month's income vs expenses
- Top spending categories
- Comparison to last month
- Savings rate

### `/finance report {period}` — Detailed Report
Generate a report for the specified period (week/month/quarter):
- Income breakdown by source (salary, freelance, crypto, etc.)
- Expense breakdown by category
- Trends and patterns
- Recommendations

### `/finance budget` — Set/Review Budget
1. Read current budget from `data/finance/budget.json`
2. If none exists: help create one based on income and goals
3. Show budget vs actual spending

## Categories
**Income:** salary, freelance, crypto, grants, content, other
**Expenses:** food, transport, utilities, subscriptions, entertainment, education, health, savings, other

## Transaction Schema
```json
{
  "id": "uuid",
  "date": "2026-03-20",
  "type": "income|expense",
  "amount": 50000,
  "currency": "NGN",
  "category": "food",
  "description": "Lunch at work",
  "source": "gtbank"
}
```
