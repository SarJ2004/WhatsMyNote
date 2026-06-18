# Database Design

## Philosophy

Store everything as records.

Avoid creating separate tables for:

```text
expenses
lendings
borrowings
reminders
facts
```

A single records table is sufficient for MVP.

---

# Table: records

```sql
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    payload_json JSON NOT NULL
);
```

---

# Record Structure

## Lending

```json
{
  "person": "Sumit",
  "amount": 500,
  "status": "pending",
  "expected_payback_by": null,
  "raw_text": "Lent Sumit 500"
}
```

---

## Expense

```json
{
  "amount": 15000,
  "category": "rent",
  "raw_text": "Paid House Rent 15000"
}
```

---

## Reminder

```json
{
  "title": "Dentist appointment",
  "due_date": "2026-06-15",
  "raw_text": "Dentist appointment on 15th June"
}
```

---

# Why JSON Storage?

Advantages:

```text
Fast development
Schema flexibility
Easy to add new record types
Minimal migrations
```

---

# Query Strategy

The database stores records.

The application performs business logic.

Example:

```text
How much money have I lent to Sumit?
```

becomes:

```text
Fetch lending records
Filter by person = Sumit
Calculate total amount
```

---

# Indexes

Recommended:

```sql
CREATE INDEX idx_user_id
ON records(user_id);

CREATE INDEX idx_type
ON records(type);

CREATE INDEX idx_created_at
ON records(created_at);
```

---

# Multi-User Design

Every record belongs to a user.

```json
{
  "user_id": "user_123"
}
```

This enables:

```text
Multiple users
Shared infrastructure
Future SaaS deployment
```

---

# Future Database Evolution

MVP:

```text
SQLite
```

Scale:

```text
PostgreSQL
```

No schema redesign should be required.

---

# Out of Scope

Not included initially:

```text
Vector Database
Graph Database
Event Sourcing
CQRS
Microservices
```

These add complexity without validating product value.
