# WhatsMyNote

WhatsMyNote is a natural-language personal finance assistant for logging and querying lending, expenses, income, and transfers.

You can type plain English like:

- I lent Sumit 500 today
- I spent 320 on groceries
- I received 50000 as salary
- I transferred 2000 from HDFC to SBI
- Show my highest expenses this month

The app extracts structured data, stores it in MySQL, and answers supported queries automatically.

---

## What It Supports

### Lending

- Create lending or borrowing records
- Update amount, person, direction, and expected payback date
- Delete one or more lending records
- Query totals, outstanding balance, differences, and filtered histories

### Expense

- Create expense records with amount, category, merchant, payment source, item, and notes
- Update existing expenses
- Delete expenses
- Query by category, merchant, payment source, item, date, and date ranges

### Income

- Create income records such as salary, cashback, refund, or bonus
- Update existing income entries
- Delete income entries
- Query by source, date, and date ranges

### Transfer

- Create transfers between accounts
- Update source account, destination account, amount, date, and notes
- Delete transfers
- Query by source account, destination account, and date filters

### Analytics

- Read-only analytics over the stored database
- Totals, counts, averages, maxima, minima, groupings, and comparisons
- Safe SQL generation with validation before execution

---

## How To Use

### 1. Create a record

Use a sentence that clearly describes the event.

Examples:

```text
I lent Sumit 500 today
```

```text
I spent 850 on office lunch
```

```text
I received 50000 as salary from Acme
```

```text
I transferred 3000 from HDFC to SBI
```

### 2. Update a record

Make the change in natural language.

Examples:

```text
Update Sumit's loan amount to 700
```

```text
Change my grocery expense date to yesterday
```

```text
Update my salary entry notes to include bonus
```

```text
Change the transfer destination to ICICI
```

### 3. Delete a record

Examples:

```text
Delete Sumit's lending record
```

```text
Delete my last expense
```

```text
Delete the salary record from June 30
```

```text
Delete the SBI transfer entry
```

### 4. Query records

Ask for one record type at a time, or ask for an analytics-style summary.

Examples:

```text
How much money have I lent to Sumit?
```

```text
Show all expenses for food this month
```

```text
How much income did I receive from salary sources?
```

```text
Show all transfers from HDFC to SBI
```

```text
What is my total spending this month?
```

```text
Which expense category is highest this year?
```

```text
Compare my income and expense totals for July
```

---

## Query Boundary

WhatsMyNote does not answer every possible database question.

It can answer:

- Supported record queries for lending, expense, income, and transfer
- Safe read-only analytics over the same data

It does not:

- Run arbitrary SQL from the user
- Modify the schema
- Insert, update, or delete records from an analytics query
- Query tables or columns outside the supported schema

If a question is outside the supported data model, the system should reject it or return a limited answer.

---

## Environment Setup

Install dependencies and configure environment variables:

```bash
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

```env
GROQ_API_KEY=your_key
DATABASE_URL=mysql+pymysql://user:password@localhost/database_name
```

Run the app:

```bash
python main.py
```

---

## Tech Stack

- Python
- LangGraph
- LangChain
- Pydantic
- SQLAlchemy
- MySQL
- Groq LLMs

---

## Workflow

```text
User Input
    ↓
Intent Detection
    ↓
Record Type Detection or Analytics Routing
    ↓
Extraction or SQL Planning
    ↓
Validation and Record Resolution
    ↓
Database Operation
    ↓
Response Generation
```

---

## Roadmap

- [x] Create records
- [x] Update records
- [x] Delete records
- [x] Query records
- [x] Aggregations and analytics
- [ ] Multi-user support
- [ ] REST API
- [ ] Web dashboard
- [ ] WhatsApp integration
- [ ] Voice input support

---

## Vision

WhatsMyNote aims to become a conversational financial memory system for managing personal lending, borrowing, expenses, income, transfers, and analytics through natural language.
