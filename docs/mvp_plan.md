# WhatsMyNote MVP - Intent Definitions

## Vision

A WhatsApp-based personal assistant that can:

- Capture information from natural language
- Store it in structured form
- Answer questions about previously stored information

Example:

User:

> Lent Sumit ₹20

System:

> Recorded a lending of ₹20 to Sumit.

Later:

User:

> How much money have I lent?

System:

> You have lent ₹20 to Sumit.

---

# Intent 1: Expense

## Description

Money spent by the user.

## Required Fields

| Field       | Type     |
| ----------- | -------- |
| amount      | number   |
| description | string   |
| category    | string   |
| timestamp   | datetime |

## Examples

- Paid rent 15000
- Bought groceries for 500
- Spent 200 on coffee
- Ordered food for 350
- Paid electricity bill 1800
- Bought a monitor for 12000
- Took an Uber for 250

## Sample Structured Output

```json
{
  "intent": "expense",
  "amount": 500,
  "description": "groceries",
  "category": "food",
  "timestamp": "2026-06-10T18:00:00Z"
}
```

---

# Intent 2: Income

## Description

Money received by the user.

## Required Fields

| Field     | Type     |
| --------- | -------- |
| amount    | number   |
| source    | string   |
| timestamp | datetime |

## Examples

- Received salary 75000
- Got freelance payment 10000
- Received refund of 200
- Earned 5000 from consulting

## Sample Structured Output

```json
{
  "intent": "income",
  "amount": 75000,
  "source": "salary",
  "timestamp": "2026-06-10T18:00:00Z"
}
```

---

# Intent 3: Lending

## Description

Money given to someone.

## Required Fields

| Field     | Type     |
| --------- | -------- |
| person    | string   |
| amount    | number   |
| status    | string   |
| timestamp | datetime |

## Examples

- Lent Sumit 20
- Gave Rahul 500
- Loaned Aman 1000
- Sent 300 to Rakesh

## Sample Structured Output

```json
{
  "intent": "lending",
  "person": "Sumit",
  "amount": 20,
  "status": "pending",
  "timestamp": "2026-06-10T18:00:00Z"
}
```

---

# Intent 4: Borrowing

## Description

Money borrowed from someone.

## Required Fields

| Field     | Type     |
| --------- | -------- |
| person    | string   |
| amount    | number   |
| status    | string   |
| timestamp | datetime |

## Examples

- Borrowed 1000 from Rahul
- Took 500 from Sumit
- Need to return 300 to Amit

---

# Intent 5: Reminder

## Description

Future event or action that should be remembered.

## Required Fields

| Field     | Type     |
| --------- | -------- |
| title     | string   |
| due_date  | datetime |
| timestamp | datetime |

## Examples

- Dentist appointment next Friday
- Renew passport in 2028
- Call mom tomorrow
- Pay rent on 1st July
- Follow up with HR next week

---

# Intent 6: Generic Fact

## Description

Information that may be useful later.

## Required Fields

| Field     | Type     |
| --------- | -------- |
| content   | string   |
| tags      | array    |
| timestamp | datetime |

## Examples

- My passport expires in 2028
- My PAN number is ABCD1234X
- My laptop warranty ends in December
- I parked my bike in basement B2

---

# Intent 7: Task

## Description

Action item that needs completion.

## Required Fields

| Field     | Type     |
| --------- | -------- |
| task      | string   |
| status    | string   |
| priority  | string   |
| timestamp | datetime |

## Examples

- Finish Razorpay onboarding
- Update resume
- Book flight tickets
- Submit tax documents

---

# Intent 8: Query

## Description

Questions asked against stored data.

## Examples

### Expense Queries

- How much did I spend this month?
- What were my expenses yesterday?
- Show food expenses.

### Lending Queries

- How much money have I lent?
- Who owes me money?
- How much does Sumit owe me?

### Reminder Queries

- What reminders do I have?
- What is due next week?

### Fact Queries

- When does my passport expire?
- Where did I park my bike?

---

# MVP Success Criteria

The system should reliably:

1. Identify the intent.
2. Extract structured fields.
3. Store the information.
4. Answer basic queries over stored records.
5. Work entirely through WhatsApp.

```

```
