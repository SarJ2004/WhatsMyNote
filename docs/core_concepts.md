# Core Concepts

WhatsMyNote is built around a powerful Natural Language Processing engine using Large Language Models (LLMs) to classify and extract your financial intents.

## The 4 Primary Intents

Every message you send is classified into exactly one of four intents:

1. **Create**: Recording a *new* financial event (e.g., "Spent 500 on pizza", "Received salary").
2. **Update**: Modifying an *existing* record (e.g., "Actually it was 600", "Change the category to Groceries").
3. **Delete**: Removing a record permanently (e.g., "Delete the last expense", "Remove that loan").
4. **Query**: Asking for analytics or historical data (e.g., "Show my expenses", "How much do I owe Rahul?").

## Record Types

Independent of the intent, the engine determines *what* type of record you are talking about. The 6 supported records are:
`expense`, `income`, `transfer`, `lending`, `budget`, and `account`.

## Context Awareness (Memory)

WhatsMyNote has a short-term memory of the conversation. This allows you to use pronouns (`it`, `that`, `this`) in follow-up messages!

**Example:**
> **You:** Spent 500 on pizza  
> *CLI:* Created Expense record  
> **You:** Actually it was 600  
> *CLI:* Updated the amount to 600  
> **You:** Delete it  
> *CLI:* Deleted the record  

## Human-in-the-Loop Interaction

The system prioritizes safety. If you ask to `delete` or `update` a record, but the AI is unsure exactly *which* record you mean (e.g., "Delete my expense"), it will NOT guess.

Instead, it searches your recent history and presents an **Interactive Checklist** right in the terminal! You can use your arrow keys and the Spacebar to safely select the correct record to modify or delete.
