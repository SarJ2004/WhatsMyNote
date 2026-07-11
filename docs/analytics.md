# Analytics & Queries

The true power of WhatsMyNote lies in its querying engine. You can ask complex financial questions in plain English, and the CLI will instantly fetch, aggregate, and visualize the data for you!

## Supported Operations

When you query, the LLM determines what mathematical operation to perform:

- **Sum**: Adding up amounts (e.g., "Total expenses", "How much did I spend").
- **Count**: Counting the number of records (e.g., "How many times did I eat out?").
- **List**: Showing individual records (e.g., "Show my expenses").
- **Difference / Net Balance**: Subtracting amounts (e.g., "What is my net income?", "Net balance with Rahul").
- **Outstanding**: Showing unpaid amounts.

---

## Filtering Capabilities

You can aggressively filter your data by:
- **Time/Date**: "This month", "Last week", "Between Jan and March", "In 2023".
- **Category/Source**: "On Food", "From Freelance".
- **Account**: "From SBI", "In my wallet".
- **Person**: "Rahul", "Alice".

## Visualizations (Charts)

If the AI determines that your query would look good as a chart, it renders it beautifully right inside your terminal!

### Bar Charts
Triggered when comparing multiple categories, accounts, or people.
> **You**: Compare my spending across categories this month  
> *Result*: Generates a colorful Bar Chart in your terminal showing Food vs Transport vs Rent!

### Pie Charts
Triggered when you want to see proportions or distributions.
> **You**: Show my expense distribution as a pie chart  
> *Result*: Draws a detailed Pie Chart showing the percentage breakdown of your spending!

## Complex Query Examples

Here are some examples of what the engine can handle:

> **You**: How much have I spent on food this week from my HDFC account?  
> *Result*: Sums up all `expense` records categorized as "Food" paid from "HDFC" where the date is within the last 7 days.

> **You**: What is the difference between my income and expenses this month?  
> *Result*: Calculates the total income this month, calculates total expenses this month, and returns your Net Savings.

> **You**: Who owes me the most money?  
> *Result*: Lists all people you've lent money to, subtracting what they've paid back, sorted by the outstanding balance!
