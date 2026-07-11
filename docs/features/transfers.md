# Internal Transfers

Sometimes you just move money between your own accounts. Instead of logging an expense from one account and income to another, you use a Transfer record.

## Supported Fields

- **Amount** *(Required)*: The amount transferred.
- **Source Account** *(Optional)*: The account money was moved *from*. Defaults to your Default Account if omitted.
- **Destination Account** *(Optional)*: The account money was moved *to*.
- **Date** *(Optional)*: Defaults to today.
- **Description** *(Optional)*: e.g., "for rent payment tomorrow".

---

## Examples

### Logging a Transfer

> **You**: Transferred 5000 from SBI to HDFC  
> *Result*: Creates a transfer of 5000. This subtracts 5000 from your SBI balance and adds 5000 to your HDFC balance.

> **You**: Put 200 into my Cash wallet  
> *Result*: If your default account is SBI, it records a 200 transfer from SBI to Cash.

### Updating a Transfer

> **You**: That transfer was actually 6000  
> *Result*: Modifies the transfer amount to 6000, and automatically recalculates the account balances.

### Deleting a Transfer

> **You**: Undo that transfer  
> *Result*: Removes the transfer and restores the balances of both accounts to their previous state.
