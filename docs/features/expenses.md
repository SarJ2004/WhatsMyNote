# Expense Tracking

Expense tracking is the most common action in WhatsMyNote. By parsing your natural language, the AI automatically maps your spending to the correct category and deducts it from the appropriate account.

## How it Works

When you log an expense, the **Expense Agent** extracts:
- `amount`: The exact numerical value (e.g., $15.00).
- `category`: The type of expense (e.g., Food, Transport). If you have budgets set up, the AI attempts to map it to one of your existing budgets.
- `account`: Where the money came from. If omitted, it automatically uses your **Default Account**.
- `expense_date`: When it happened (defaults to today).
- `notes`: Any context you provided.

## Example Interactions

### 1. Simple Expense (Uses Default Account)
> **You:** "I spent $15 on coffee today."
>
> **AI:** "I will log an expense of $15.00 for 'Coffee' from your Default account (SBI). Is this correct? [y/N]"

### 2. Specifying an Account
> **You:** "I bought a $1200 laptop using my HDFC Credit Card."
>
> **AI:** "I will log an expense of $1200.00 for 'Electronics/Laptop' from your 'HDFC Credit Card' account. Is this correct? [y/N]"

### 3. Retroactive Expenses
> **You:** "Yesterday I spent $45 on gas."
>
> **AI:** "I will log an expense of $45.00 for 'Gas' from your Default account (SBI) dated for yesterday. Is this correct? [y/N]"

## Edge Cases & Error Handling

- **Missing Data:** If you say *"I bought coffee"*, the AI knows the amount is missing. The Human-in-the-Loop system will intervene and say: *"I understand you bought coffee, but how much did it cost?"*
- **Currency:** The system currently standardizes on your default currency, though future updates will support multi-currency parsing.
