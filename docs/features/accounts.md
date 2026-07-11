# Accounts Management

Accounts represent where your money is physically held (e.g., SBI, Cash, Crypto Wallet). WhatsMyNote automatically computes the **Current Balance** of your accounts based on your entire transaction history.

## Supported Fields

- **Name** *(Required)*: The name of the account (e.g., SBI, Wallet).
- **Opening Balance** *(Optional)*: The initial amount in the account before you started tracking. Defaults to 0.
- **Is Default** *(Optional)*: True/False. Sets the account as the fallback for all transactions.

---

## How Balances Work

Your Current Balance is **dynamically calculated** at all times:
`Opening Balance + Income Received + Incoming Transfers + Borrowed Money - Expenses - Outgoing Transfers - Lent Money`

## Examples

### Creating an Account

> **You**: Add an HDFC account with 5000 in it  
> *Result*: Creates the "HDFC" account with an opening balance of 5000.

### Setting the Default Account

> **You**: Make HDFC my default account  
> *Result*: Updates HDFC to `is_default=True` and unsets the previous default account.

### Updating Account Balance

> **You**: Actually, my HDFC opening balance was 6000  
> *Result*: Updates the opening balance. The *Current Balance* will instantly recalculate to reflect this change across all your history!

### Querying Accounts

> **You**: Show my account balances  
> *Result*: Lists all your accounts along with their perfectly calculated Current Balances.

> **You**: What's my balance in SBI?  
> *Result*: Shows the balance specifically for SBI.
