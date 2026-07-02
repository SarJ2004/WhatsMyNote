# Budget And Analytics Plan

## Goal

Add first-class support for:

- opening balances for named accounts
- monthly or category budgets
- current account balance summaries
- budget variance reporting
- higher-order analytics over all financial records

## Core Idea

User starts from initial financial position.

That means store:

- opening balance per account
- optional initial cash position
- optional budgets per category or time window

Then compute current state from:

- opening balance
- income
- expenses
- transfers
- lending if you want outstanding debt in net-worth view

## Suggested Record Types

### Account

Stores named places money lives.

Examples:

- SBI
- HDFC
- Wallet
- Cash

Fields:

- name
- opening_balance
- currency
- notes

### Budget

Stores planned spend limit.

Examples:

- groceries this month = 10000
- transport this month = 3000
- overall monthly budget = 50000

Fields:

- scope
- category
- amount
- period
- start_date
- end_date

## Analytics Levels

### Level 1

- expense totals
- income totals
- lending totals
- transfer totals

### Level 2

- savings = income - expenses
- account balance summaries
- budget remaining

### Level 3

- category trend
- source trend
- account trend
- overspend detection

### Level 4

- net worth estimate
- financial health summary
- LLM-written insights from SQL results

## Architecture

Use same pattern as current analytics lane:

```text
User
  ↓
Analytics Planner
  ↓
Safe Text-to-SQL
  ↓
SQL Validator
  ↓
MySQL
  ↓
Structured Results
  ↓
Insight Generator
  ↓
Final Answer
```

## Build Order

1. Add account and budget tables.
2. Add setup flow for initial balances.
3. Add budget create/update/query flows.
4. Extend analytics schema context.
5. Add prebuilt SQL templates for balance and budget math.
6. Add insight layer for plain-language summaries.

## Important Rule

Analytics must stay read-only.

Budget and balance setup can create or update record rows, but analytics path must never write.
