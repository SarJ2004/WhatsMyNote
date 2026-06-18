# Components

## Architecture

```text
WhatsApp
    ↓
Gateway
    ↓
Extractor
    ↓
Action Executor
    ↓
Database
    ↓
Response Generator
```

---

# 1. WhatsApp Gateway

## Responsibilities

Receive messages.

Send replies.

Maintain session information.

---

## Technology

```text
Baileys
```

---

## Input

```json
{
  "user_id": "123",
  "message": "Lent Sumit 500"
}
```

---

## Output

```json
{
  "user_id": "123",
  "message": "Recorded lending of ₹500 to Sumit."
}
```

---

# 2. Extractor

## Responsibilities

Convert natural language into Action JSON.

This is the only AI-powered component.

---

## Input

```text
Lent Sumit 500
```

---

## Output

```json
{
  "action": "create_record",
  "records": [...]
}
```

---

## Technology

```text
OpenAI
Gemini
Claude
```

Any provider can be swapped in.

---

# 3. Action Executor

## Responsibilities

Execute extracted actions.

No LLM calls.

Pure backend logic.

---

## Supported Actions

```text
create_record
query_records
```

---

## Example

Input:

```json
{
  "action": "create_record"
}
```

Output:

```json
{
  "success": true
}
```

---

# 4. Database Layer

## Responsibilities

Store records.

Fetch records.

Run aggregations.

---

## Example Operations

```text
insert_record
find_records
aggregate_records
```

---

# 5. Response Generator

## Responsibilities

Convert raw query results into user-facing messages.

---

## Example

Input:

```json
{
  "total_amount": 2500
}
```

Output:

```text
You lent ₹2,500 this month.
```

---

# Future Components

```text
Reminder Scheduler
Vector Search
Analytics Engine
Calendar Sync
Email Sync
Voice Processing
```

These are intentionally excluded from MVP.
