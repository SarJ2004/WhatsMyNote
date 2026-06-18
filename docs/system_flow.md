# System Flow

## Overview

WhatsMyNote converts natural language messages into structured actions and executes them against a personal knowledge store.

The system follows:

```text
User Message
    ↓
Message Receiver
    ↓
Extractor (LLM)
    ↓
Action JSON
    ↓
Action Executor
    ↓
Database
    ↓
Response Generator
    ↓
User Reply
```

---

# Flow 1: Create Record

## Example

User:

```text
Lent Sumit 500
```

---

## Step 1: Receive Message

```json
{
  "message": "Lent Sumit 500",
  "user_id": "user_123"
}
```

---

## Step 2: Extract Action

LLM returns:

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "lending",
      "person": "Sumit",
      "amount": 500,
      "status": "pending",
      "raw_text": "Lent Sumit 500"
    }
  ]
}
```

---

## Step 3: Execute Action

Action Executor stores record.

---

## Step 4: Generate Response

```text
Recorded lending of ₹500 to Sumit.
```

---

# Flow 2: Query Records

## Example

User:

```text
How much money have I lent to Sumit this month?
```

---

## Step 1: Extract Query

```json
{
  "action": "query_records",
  "aggregation": "sum",
  "field": "amount",
  "filters": {
    "type": "lending",
    "person": "Sumit",
    "period": "current_month"
  }
}
```

---

## Step 2: Execute Query

Database returns:

```json
{
  "total_amount": 2500
}
```

---

## Step 3: Generate Response

```text
You lent ₹2,500 to Sumit this month.
```

---

# Flow 3: Clarification Required

## Example

User:

```text
I spent some money
```

---

## Step 1: Extract Action

```json
{
  "action": "clarification_required",
  "message": "How much money did you spend?"
}
```

---

## Step 2: Reply

```text
How much money did you spend?
```

---

# MVP Scope

Supported actions:

```text
create_record
query_records
clarification_required
```

Not supported initially:

```text
update_record
delete_record
bulk_operations
```

---

# Future Flow

Future versions may include:

```text
Voice Notes
Images
OCR
Email Parsing
Calendar Integration
```
