# Income Tracking

Income tracking allows you to log money coming *into* your accounts. This could be your monthly salary, freelance earnings, or a random cash gift.

When you log an income event, the **Income Agent** ensures the specified amount is *added* to the balance of the designated account.

## How it Works

The Income Agent extracts:
- `amount`: The exact numerical value (e.g., $5000.00).
- `source`: Where the money came from (e.g., Employer, Freelance Client).
- `account`: Where the money was deposited. If omitted, it automatically goes into your **Default Account**.
- `income_date`: When you received it (defaults to today).
- `notes`: Any context you provided.

## Example Interactions

### 1. Simple Income (Uses Default Account)
> **You:** "I just got paid my $5000 salary."
>
> **AI:** "I will log an income of $5000.00 from 'Salary' into your Default account (SBI). Is this correct? [y/N]"

### 2. Specifying a Source and Account
> **You:** "My freelance client paid me $800 directly into my PayPal account."
>
> **AI:** "I will log an income of $800.00 from 'Freelance Client' into your 'PayPal' account. Is this correct? [y/N]"

### 3. Combining Entities
> **You:** "Grandma gave me $50 cash for my birthday."
>
> **AI:** "I will log an income of $50.00 from 'Grandma' into your 'Cash' account, with the note 'Birthday'. Is this correct? [y/N]"

## Analytics

You can easily query your income using the text-to-SQL analytics engine:
- *"How much did I make from freelance work this year?"*
- *"Show me my total income vs total expenses for last month."*
