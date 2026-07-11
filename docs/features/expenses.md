# Expense Tracking

WhatsMyNote allows you to effortlessly log and track your expenses using natural language.

## Supported Fields

When logging an expense, the AI attempts to extract the following information:
- **Amount** *(Required)*: The total cost.
- **Category** *(Optional)*: e.g., Food, Transport, Rent, Entertainment. If none is provided, it defaults to "General".
- **Payment Source / Account** *(Optional)*: e.g., SBI, HDFC, Cash. If none is provided, it falls back to your Default Account.
- **Date** *(Optional)*: Defaults to today's date if not explicitly mentioned (e.g., "yesterday", "on Monday").
- **Description** *(Optional)*: Any extra context (e.g., "at DMart", "for the party").

---

## Examples

### Creating an Expense

> **You**: Spent 500 on pizza yesterday  
> *Result*: Creates an expense of 500 under the "Food" category, dated yesterday.

> **You**: Paid 2000 for electricity bill from HDFC  
> *Result*: Creates an expense of 2000 under "Utilities" or "Bills", paid from the "HDFC" account.

### Updating an Expense

> **You**: Actually, that pizza was 600  
> *Result*: Updates the amount of the last expense to 600.

> **You**: Change the category of the electricity bill to Home  
> *Result*: Updates the category to "Home".

### Deleting an Expense

> **You**: Delete the pizza expense  
> *Result*: Removes the record. If ambiguous, the CLI will present a checklist of recent expenses for you to select from.

### Querying Expenses

> **You**: How much did I spend this month?  
> *Result*: Calculates the total sum of expenses for the current month.

> **You**: Show all my food expenses  
> *Result*: Lists all records categorized as Food.
