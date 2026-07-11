# WhatsMyNote

WhatsMyNote is a natural-language personal finance assistant for logging and querying lending, expenses, income, and transfers. It uses advanced **Llama 3 LLMs** to extract structured data, store it in MySQL, and answer your complex queries accurately.

## 🚀 Bring Your Own Key (BYOK) Architecture
WhatsMyNote now supports a secure **BYOK architecture**. You bring your own **Groq API key** to power the inference engine locally and securely. 

On your first run, the app will prompt you for your `GROQ_API_KEY`. It is stored securely in a local `.env` file and is never exposed. The application uses state-of-the-art Groq models:
- **`llama-3.3-70b-versatile`** for reasoning, intent classification, and SQL generation.
- **`llama-3.1-8b-instant`** for fast and efficient data extraction.

---

## 🛠 What It Supports & Examples

### 📉 Expenses
Track where your money is going.
- Create expense records with amount, category, merchant, payment source, item, and notes.
- **Example:** `I spent 320 on groceries at Walmart using HDFC`
- **Example:** `Update my last grocery expense amount to 400`
- **Example:** `Delete the Walmart expense`
- **Example:** `Show my highest expenses this month`

### 💰 Income
Record earnings, cashback, or refunds.
- **Example:** `I received 50000 as salary from Acme`
- **Example:** `Update my salary entry notes to include the July bonus`
- **Example:** `How much income did I receive from salary sources this year?`

### 🤝 Lending & Borrowing
Keep track of who owes you, and who you owe.
- **Example:** `I lent Sumit 500 today`
- **Example:** `Update Sumit's loan amount to 700`
- **Example:** `How much money have I lent to Sumit?`

### 🔁 Transfers
Record money moving between your own accounts.
- **Example:** `I transferred 3000 from HDFC to SBI`
- **Example:** `Change the transfer destination to ICICI`
- **Example:** `Show all transfers from HDFC this month`

### 📊 Budgets and Balances
Track your overall financial health.
- Set opening balances for your accounts (e.g., cash, wallet, SBI).
- Track category budgets (e.g., groceries, transport) or an `Overall` limit.
- **Example:** `Set opening balance for SBI to 50000`
- **Example:** `Set monthly budget for groceries to 10000`
- **Example:** `What is my current balance in SBI?`
- **Example:** `How much budget do I have left for groceries this month?`

### 📈 Analytics (Read-Only)
Run advanced queries without touching write access.
- Safe SQL generation with automated validation.
- Prefix queries with `sql:` for advanced read-only raw queries.
- **Example:** `What is my total spending this month?`
- **Example:** `Compare my income and expense totals for July`
- **Example:** `What is my net worth estimate?`

---

## ⚙️ Environment Setup

Install dependencies and start your virtual environment:

```bash
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

Set up your database connection string in your `.env` (or let the app default to standard SQLite/MySQL connection):
```env
DATABASE_URL=mysql+pymysql://user:password@localhost/database_name
```

Run the app. It will prompt you for your `GROQ_API_KEY` on the first launch!
```bash
python app/main.py
```

---

## 🏗 Tech Stack

- **Python** for core logic.
- **LangGraph & LangChain** for robust stateful intent routing and HITL (Human-in-the-Loop) flows.
- **Pydantic** for extraction validation.
- **SQLAlchemy & MySQL** for data persistence.
- **Groq LLMs (Llama 3)** for lightning-fast, high-quality inference.

---

## 🚀 Vision
WhatsMyNote aims to become a fully conversational financial memory system, helping you control your lending, borrowing, expenses, income, and transfers through pure natural language.
