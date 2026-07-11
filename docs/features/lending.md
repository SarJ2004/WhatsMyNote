# Lending & Borrowing

Lending tracking lets you manage debts effectively. It handles both money you lent to others (Lent) and money you borrowed from others (Borrowed).

## Supported Fields

- **Amount** *(Required)*: The amount owed.
- **Person** *(Required)*: The name of the person (e.g., Rahul, Alice).
- **Direction** *(Required)*: Whether you "lent" it or "borrowed" it.
- **Account** *(Optional)*: The account the money came from or went to. Defaults to your Default Account.
- **Expected Payback By** *(Optional)*: A deadline for the debt (e.g., "by next Friday").

---

## Examples

### Creating a Lending Record

> **You**: Lent Rahul 500  
> *Result*: Creates a lending record of 500 with direction "lent" to Rahul.

> **You**: Borrowed 1000 from Alice to my HDFC account, will pay back next week  
> *Result*: Creates a record of 1000 borrowed from Alice, deposited to HDFC, with an `expected_payback_by` date of next week.

### Settling Debts (Updating/Deleting)

When Rahul pays you back, you have two options:
1. **Update**: Reduce the amount if it's a partial payment.
   > **You**: Rahul paid me back 200  
   > *Result*: Reduces the outstanding loan to 300.
2. **Delete/Settle**: Mark it completely paid off.
   > **You**: Rahul paid me back in full / Settle Rahul's debt  
   > *Result*: The CLI asks you to confirm, and then Deletes the outstanding loan record.

### Querying Lending

> **You**: How much does Rahul owe me?  
> *Result*: Sums up all outstanding "lent" records for Rahul.

> **You**: Who owes me money?  
> *Result*: Lists all people you have "lent" money to.

> **You**: What is my net balance with Alice?  
> *Result*: Calculates the difference between what you lent her and what you borrowed from her.
