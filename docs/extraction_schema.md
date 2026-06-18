# Extraction Schema v1

## Design Principles

### 1. LLMs extract, they do not answer

The LLM's responsibility is to convert natural language into structured actions.

Example:

User:

```text
How much money have I lent to Sumit this month?
```

LLM:

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

The backend executes the query.

---

### 2. Extract queryable fields explicitly

Avoid storing information inside descriptions.

Bad:

```json
{
  "description": "Sarthak lent Sumit ₹500"
}
```

Good:

```json
{
  "person": "Sumit",
  "amount": 500
}
```

---

### 3. Preserve original user text

Every record should retain the original message.

```json
{
  "raw_text": "Lent Sumit 500"
}
```

---

### 4. One real-world event = one record

Example:

```text
Lent Sumit 500 and Rahul 300
```

Should generate two lending records.

---

# Supported Actions

```text
create_record
query_records
update_record
delete_record
clarification_required
```

---

# Record Schema

All records should conform to the following structure.

```json
{
  "id": "uuid",
  "type": "expense",
  "created_at": "timestamp",
  "raw_text": "original user message"

  // record-specific fields
}
```

---

# Supported Record Types

```text
expense
income
lending
borrowing
reminder
fact
task
```

---

# Create Record Examples

## 1. Lending

Input:

```text
Lent Sumit 500
```

Output:

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "lending",
      "person": "Sumit",
      "amount": 500,
      "status": "pending",
      "expected_payback_by": null,
      "raw_text": "Lent Sumit 500"
    }
  ]
}
```

---

## 2. Expense

Input:

```text
Paid House Rent 15000
```

Output:

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "expense",
      "amount": 15000,
      "category": "rent",
      "raw_text": "Paid House Rent 15000"
    }
  ]
}
```

---

## 3. Income

Input:

```text
Received 2000 from Sumit
```

Output:

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "income",
      "amount": 2000,
      "source": "Sumit",
      "raw_text": "Received 2000 from Sumit"
    }
  ]
}
```

---

## 4. Borrowing

Input:

```text
Borrowed 2000 from Sumit
```

Output:

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "borrowing",
      "person": "Sumit",
      "amount": 2000,
      "status": "pending",
      "expected_payback_by": null,
      "raw_text": "Borrowed 2000 from Sumit"
    }
  ]
}
```

---

## 5. Reminder

Input:

```text
Dentist appointment on 15th June
```

Output:

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "reminder",
      "title": "Dentist appointment",
      "due_date": "2026-06-15",
      "raw_text": "Dentist appointment on 15th June"
    }
  ]
}
```

---

## 6. Fact

Input:

```text
Arun uncle lives in Ranchi
```

Output:

```json
{
  "action": "create_record",
  "records": [
    {
      "type": "fact",
      "raw_text": "Arun uncle lives in Ranchi"
    }
  ]
}
```

---

## 7. Multiple Records

Input:

```text
Lent Sumit 500 and Rahul 300
```

Output:

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
    },
    {
      "type": "lending",
      "person": "Rahul",
      "amount": 300,
      "status": "pending",
      "raw_text": "Lent Rahul 300"
    }
  ]
}
```

---

# Query Records

## Query Structure

```json
{
  "action": "query_records",
  "filters": {},
  "aggregation": null,
  "field": null
}
```

---

## Example 1

Input:

```text
How much money have I lent?
```

Output:

```json
{
  "action": "query_records",
  "aggregation": "sum",
  "field": "amount",
  "filters": {
    "type": "lending"
  }
}
```

---

## Example 2

Input:

```text
How much money have I lent to Sumit this month?
```

Output:

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

## Example 3

Input:

```text
What reminders do I have?
```

Output:

```json
{
  "action": "query_records",
  "filters": {
    "type": "reminder"
  }
}
```

---

## Example 4

Input:

```text
How much did I spend on rent this month?
```

Output:

```json
{
  "action": "query_records",
  "aggregation": "sum",
  "field": "amount",
  "filters": {
    "type": "expense",
    "category": "rent",
    "period": "current_month"
  }
}
```

---

# Update Records

## Update Structure

```json
{
  "action": "update_record",
  "filters": {},
  "updates": {}
}
```

---

## Example 1

Input:

```text
Sumit returned 200
```

Output:

```json
{
  "action": "update_record",
  "filters": {
    "type": "lending",
    "person": "Sumit"
  },
  "updates": {
    "amount_returned": 200
  }
}
```

---

## Example 2

Input:

```text
Dentist appointment moved to 20th June
```

Output:

```json
{
  "action": "update_record",
  "filters": {
    "type": "reminder",
    "title": "Dentist appointment"
  },
  "updates": {
    "due_date": "2026-06-20"
  }
}
```

---

# Delete Records

## Delete Structure

```json
{
  "action": "delete_record",
  "filters": {}
}
```

---

## Example 1

Input:

```text
Delete my dentist appointment reminder
```

Output:

```json
{
  "action": "delete_record",
  "filters": {
    "type": "reminder",
    "title": "Dentist appointment"
  }
}
```

---

## Example 2

Input:

```text
Forget that Arun uncle lives in Ranchi
```

Output:

```json
{
  "action": "delete_record",
  "filters": {
    "type": "fact",
    "raw_text": "Arun uncle lives in Ranchi"
  }
}
```

---

# Clarification Required

## Example 1

Input:

```text
Remind me about the meeting
```

Output:

```json
{
  "action": "clarification_required",
  "message": "When should I remind you about the meeting?"
}
```

---

## Example 2

Input:

```text
I spent some money
```

Output:

```json
{
  "action": "clarification_required",
  "message": "How much money did you spend?"
}
```

````

---

# Future Extensions

Potential future actions:

```text
create_category
merge_records
split_record
bulk_update
bulk_delete
````

Potential future record types:

```text
investment
subscription
habit
goal
meeting_note
contact
travel
```
