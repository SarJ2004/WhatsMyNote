# Income Tracking

Keep track of your earnings, salaries, refunds, and side-hustle revenue.

## Supported Fields

When logging income, the AI attempts to extract the following information:
- **Amount** *(Required)*: The total money received.
- **Source** *(Optional)*: e.g., Salary, Freelance, Refund, Alice. Defaults to "General".
- **Deposit Account** *(Optional)*: e.g., SBI, HDFC, Wallet. Where the money was deposited. If omitted, defaults to your Default Account.
- **Date** *(Optional)*: Defaults to today's date if not specified.
- **Description** *(Optional)*: Any extra context.

---

## Examples

### Logging Income

> **You**: Got my 50000 salary deposited in HDFC  
> *Result*: Creates an income record of 50000 from "Salary", deposited into the "HDFC" account.

> **You**: Received 500 as a refund from Amazon  
> *Result*: Creates an income record of 500 from "Amazon".

### Updating Income

> **You**: Actually my salary was 55000  
> *Result*: Updates the amount of the salary record to 55000.

### Deleting Income

> **You**: Delete the Amazon refund  
> *Result*: Safely removes the record.

### Querying Income

> **You**: How much did I earn this year?  
> *Result*: Sums up all your income records for the current year.

> **You**: Show my freelance income  
> *Result*: Lists all income records where the source is categorized as "Freelance".
