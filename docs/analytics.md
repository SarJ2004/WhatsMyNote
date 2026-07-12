# Analytics & Text-to-SQL

One of the most powerful features of WhatsMyNote is its ability to instantly convert your natural language questions into complex, secure SQL queries to analyze your data. 

Instead of navigating through menus or setting up custom dashboards, you simply ask the AI what you want to know.

## How it Works

When the **Supervisor Agent** determines that your message is an analytical question (e.g., *"How much did I spend this month?"* rather than a command like *"I spent $5"*), it routes your query to the **SQL Agent**.

1. The SQL Agent is provided with the strict SQL schema of your database tables (`expense_records`, `income_records`, `account_records`, etc.).
2. It writes a highly optimized PostgreSQL query based on your question.
3. It securely executes the query against your database.
4. It formats the raw data into a beautiful, rich terminal chart or table.

## Example Queries

### Basic Summaries
> **You:** "What is my total income this month?"
> 
> **AI:** *(Generates `SUM(amount)` over `income_records` filtering by current month)*
> "Your total income for this month is $5,000."

### Categorical Breakdown
> **You:** "Show me a breakdown of my expenses by category for the last 30 days"
>
> **AI:** *(Generates a `GROUP BY category` query)*
> 
> ```text
> ╭─────────────────────────────── Analytics Chart ────────────────────────────────╮       
> │                         Spending by Category                                │
> │         ┌──────────────────────────────────────────────────┐                │
> │         │██████████████████████████                        │                │
> │         │██████████████████████████                        │                │
> │   Others┤██████████████████████████                        │                │
> │         │██████████████████████████                        │                │
> │         │████████████████████████████████                  │                │
> │ Shopping┤████████████████████████████████                  │                │
> │         │████████████████████████████████                  │                │
> │         │████████████████████████████████                  │                │
> │         │██████████████████████████████████████████████████│                │
> │     Food┤██████████████████████████████████████████████████│                │
> │         │██████████████████████████████████████████████████│                │
> │         │██████████████████████████████████████████████████│                │
> │         └┬───────────┬────────────┬───────────┬───────────┬┘                │
> │          0          20           40          60          80                 │
> ╰────────────────────────────────────────────────────────────────────────────────╯
> ```

### Complex Filtering
> **You:** "How much money has Alex borrowed from me in total, and how much has he paid back?"
>
> **AI:** *(Generates a query analyzing the `lending_records` grouping by the borrower 'Alex', summing both the lent amount and repaid amount)*

## Security & Privacy
The SQL Agent runs with strict **Read-Only** access parameters during analytics generation, meaning the AI literally cannot accidentally `DROP TABLE` or mutate your data during an analytical query. Furthermore, Supabase Row Level Security (RLS) guarantees the AI can only ever query data that strictly belongs to your OAuth user ID.
