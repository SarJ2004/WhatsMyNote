# Budgets Management

WhatsMyNote allows you to set up recurring spending limits for specific categories, helping you track your expenses over a specific period.

## Supported Fields

- **Category** *(Required)*: The category to budget for (e.g., Food, General, Overall). "Overall" applies to all expenses combined.
- **Limit Amount** *(Required)*: The maximum amount you want to spend.
- **Period** *(Optional)*: E.g., Monthly, Weekly, Yearly. Defaults to Monthly.
- **Notes** *(Optional)*: Any extra context for the budget.

---

## Examples

### Setting up a Budget

> **You**: Set a monthly budget of 5000 for Food  
> *Result*: Creates a budget record for the "Food" category with a 5000 limit per month.

> **You**: Limit my overall expenses to 20000 this month  
> *Result*: Creates an "Overall" budget of 20000.

### Tracking your Budget

To see how much you have spent against your budgets, simply query it! WhatsMyNote's analytics engine will automatically calculate your current spending for the month in that category and compare it to the limit.

> **You**: Show my budgets  
> *Result*: Lists your active budgets, alongside a visualization of how much of the limit you've consumed!

### Updating a Budget

> **You**: Increase my Food budget to 6000  
> *Result*: Updates the limit amount to 6000.

### Deleting a Budget

> **You**: Delete the food budget  
> *Result*: Removes the budget limit completely.
