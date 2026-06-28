from datetime import date
from pydantic import BaseModel
from typing import Literal, List


class ExpenseInput(BaseModel):
    amount: int
    category: str | None = None
    merchant: str | None = None
    payment_source: str | None = None
    expense_date: date | None = None
    notes: str | None = None


class CreateExpense(BaseModel):
    action: Literal["create"]
    records: List[ExpenseInput]
