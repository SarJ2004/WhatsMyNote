# The Canonical Data Model Design

- Every captured item becomes a record

```json
{
  "id": "uuid",
  "type": "expense",
  "created_at": "...",
  "data": {}
}
```

## Examples

### 1. Expense

```json
{
  "id": "123",
  "type": "expense",
  "created_at": "...",
  "data": {
    "amount": 500,
    "description": "groceries",
    "category": "food"
  }
}
```

### 2. Lending

```json
{
  "id": "123",
  "type": "expense",
  "created_at": "...",
  "data": {
    "amount": 500,
    "description": "groceries",
    "category": "food"
  }
}
```

### 3. Reminder

```json
{
  "id": "125",
  "type": "reminder",
  "created_at": "...",
  "data": {
    "title": "Dentist appointment",
    "due_date": "2026-06-15"
  }
}
```

## Basic Parser Response

```json
{
  "action": "create_record",
  "record_type": "lending",
  "data": {
    "person": "Sumit",
    "amount": 20
  }
}
```

- Furthermore, many other actions such as query, update and delete
  records can also be supported by the parser. For example, to query all lending records, the response can be:

```json
{
  "action": "query_records",
  "record_type": "lending",
  "filters": {
    "person": "Sumit"
  }
}
```

- In case of multiple records, the response can be an array of records.
- ex - Lent sumit 500 and rahul 300

```json
[
  {
    "type": "lending",
    "person": "Sumit",
    "amount": 500
  },
  {
    "type": "lending",
    "person": "Rahul",
    "amount": 300
  }
]
```

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "lending",
      "data": {
        "person": "Sumit",
        "amount": 500
      }
    },
    {
      "type": "lending",
      "data": {
        "person": "Rahul",
        "amount": 300
      }
    }
  ]
}
```

## Generic LLM Response

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "lending",
      "data": {
        "person": "Sumit",
        "amount": 500
      }
    }
  ]
}
```

## LLM Response to Ambiguous messages

- ex - Need to remember something
- LLM response:

```json
{
  "action": "clarification_required"
  "message": "What would you like me to remember?"
}
```
