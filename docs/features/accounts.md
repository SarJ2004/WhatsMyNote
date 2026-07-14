# Accounts Management

Accounts form the foundational layer of your financial tracking in WhatsMyNote. Every transaction (Expense, Income, Transfer) is intrinsically linked to an Account.

An account can represent anything where money is stored: a Bank Account, a physical Cash wallet, a Credit Card, or a digital wallet like PayPal.

## The Default Account
When you first set up the app, you are prompted to define a **Default Account**. 
This is an incredibly powerful feature. Because WhatsMyNote has a global context, if you simply say *"I bought lunch for $10"*, the AI automatically deduces that the money came out of your Default Account, saving you from having to type *"from my checking account"* every single time.

## Example Interactions

Here are some ways you can interact with the Account Agent:

### 1. Creating a New Account
> **You:** "I just opened a new Savings account at Chase with $500 in it."
>
> **AI:** "I will create a new account named 'Chase Savings' with an opening balance of $500.00. Is this correct? [y/N]"

### 2. Modifying an Existing Account
> **You:** "Change the name of my Chase Savings account to 'Emergency Fund'."
>
> **AI:** "I will rename the account 'Chase Savings' to 'Emergency Fund'. Is this correct? [y/N]"

### 3. Setting a New Default
> **You:** "Make my HDFC account the default one from now on."
>
> **AI:** "I will update your default account to 'HDFC'. Is this correct? [y/N]"

### 4. Viewing Balances
> **You:** "What are my current account balances?"
>
> **AI:** 
> 
> ```text
> ╭────────────── Account Balances ──────────────╮
> │                                              │
> │  Default (SBI): $2,450.00                    │
> │  Cash Wallet: $120.00                        │
> │  Emergency Fund: $5,000.00                   │
> │                                              │
> ╰──────────────────────────────────────────────╯
> ```

## Edge Cases & Error Handling

- **Missing Account:** If you try to log a transaction from an account that doesn't exist (e.g., *"I spent $50 from my PayPal account"* when you haven't created a PayPal account), the AI's Human-in-the-Loop mechanism will intervene, alert you that the account doesn't exist, and ask if you meant your default account or if you want to create a new one.
