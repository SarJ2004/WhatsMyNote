# WhatsMyNote

An AI-powered personal finance assistant that lets you manage lending and borrowing records using natural language.

Instead of manually filling forms or writing SQL queries, simply type:

- "I lent Sumit ₹500 today"
- "Update Sumit's amount to 700"
- "Delete Rohan's record"
- "How much money have I lent to Sumit?"

The system understands your intent, extracts structured data, and performs the required database operations automatically.

---

## Features

### Record Management

- Create lending/borrowing records using natural language
- Update existing records
- Delete records
- Query records conversationally

### AI-Powered Understanding

- Intent classification
- Structured information extraction
- Query planning
- Record resolution and matching

### Database Support

- SQLAlchemy ORM
- MySQL backend
- Structured schema validation using Pydantic

### Agent Workflow

Built using LangGraph with dedicated nodes for:

1. Intent Detection
2. Record Extraction
3. Query Planning
4. Record Resolution
5. CRUD Execution
6. Response Generation

---

## Example Commands

### Create Records

```text
I lent Sumit 500 rupees
```

```text
I lent Sumit 500 and Rohan 200
```

### Update Records

```text
Update Sumit's amount to 700
```

```text
Change Rohan's payback date to July 1st
```

### Delete Records

```text
Delete Sumit's record
```

```text
Delete all records
```

### Query Records

```text
How much money have I lent to Sumit?
```

```text
Show all pending repayments
```

```text
What is the difference between the money I lent to Sumit and Rohan?
```

---

## Project Structure

```text
.
├── agents/
│   ├── intent_classifier.py
│   ├── record_extractor.py
│   └── query_planner.py
│
├── db/
│   ├── config.py
│   └── models.py
│
├── models/
│   ├── state.py
│   ├── record_models.py
│   ├── update_record_model.py
│   └── delete_record_model.py
│
├── services/
│   ├── record_resolver.py
│   ├── record_creator.py
│   ├── record_updater.py
│   └── record_deleter.py
│
├── graph/
│   └── workflow.py
│
└── main.py
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

## How It Works

```text
User Input
    ↓
Intent Classification
    ↓
Record Extraction / Query Planning
    ↓
Record Resolution
    ↓
Database Operation
    ↓
Response Generation
```

---

## Installation

```bash
git clone https://github.com/SarJ2004/whatsmynote.git

cd whatsmynote

uv venv
source .venv/bin/activate

uv pip install -r requirements.txt
```

Configure environment variables:

```env
GROQ_API_KEY=your_key
DATABASE_URL=mysql+pymysql://user:password@localhost/database_name
```

Run the application:

```bash
python main.py
```

---

## Roadmap

- [x] Create records
- [x] Update records
- [x] Delete records
- [ ] Query planner
- [ ] Aggregations and analytics
- [ ] Multi-user support
- [ ] REST API
- [ ] Web dashboard
- [ ] WhatsApp integration
- [ ] Voice input support

---

## Vision

WhatsMyNote aims to become a conversational financial memory system that allows users to manage personal lending, borrowing, expenses, and financial notes through natural language interactions.
