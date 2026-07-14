# Budget Tracking

Budgets in WhatsMyNote act as financial guardrails. You can establish monthly (or weekly) spending limits for specific categories, and the AI will automatically track your expenses against them.

When you log an expense, the AI will intelligently categorize it. If it falls under a category you have a budget for, it will deduct it from your remaining budget.

## Example Interactions

Here are some ways you can interact with the Budget Agent:

### 1. Creating a Budget
> **You:** "Set a monthly budget of $400 for groceries."
>
> **AI:** "I will create a new budget for 'Groceries' with a limit of $400.00 per month. Is this correct? [y/N]"

### 2. Updating a Budget
> **You:** "Increase my Food budget to $600."
>
> **AI:** "I will update your 'Food' budget from $500.00 to $600.00. Is this correct? [y/N]"

### 3. Checking Remaining Budgets
> **You:** "How am I doing on my budgets this month?"
>
> **AI:** 
> ```text
> ╭──────────────── Budget Status ─────────────────╮
> │                                                │
> │  Groceries: $150.00 remaining (of $400.00)     │
> │  Food: $50.00 remaining (of $600.00)           │
> │  Entertainment: $20.00 OVER BUDGET             │
> │                                                │
> ╰────────────────────────────────────────────────╯
> ```

## Edge Cases & Error Handling

- **Ambiguous Categories:** If you set a budget for "Food", but later say *"I spent $50 at the supermarket"*, the AI is smart enough to realize "supermarket" falls under your "Food" (or "Groceries") budget. 
- **Exceeding Budget:** While the AI will not stop you from logging an expense that exceeds your budget, it can warn you if you ask for a status update.
