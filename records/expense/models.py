from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, List, Union
from enum import Enum
from models.selectors import RecordSelector


from datetime import date
from pydantic import BaseModel, Field, field_validator
from typing import Literal, List


class ExpenseInput(BaseModel):
    amount: int
    category: str | None = None
    merchant: str | None = None
    payment_source: str | None = None
    expense_date: date | None = None

    item: str | None = None
    notes: str | None = None


class CreateExpense(BaseModel):
    action: Literal["create"]
    records: List[ExpenseInput]


class UpdateOperation(str, Enum):
    SET = "set"
    ADD = "add"
    SUB = "subtract"
    MULTIPLY = "multiply"


class ExpenseField(str, Enum):
    AMOUNT = "amount"
    CATEGORY = "category"
    MERCHANT = "merchant"
    PAYMENT_SOURCE = "payment_source"
    EXPENSE_DATE = "expense_date"
    NOTES = "notes"


class ExpenseFieldUpdate(BaseModel):
    field: ExpenseField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[
        str,
        int,
        float,
        date,
    ]


class UpdateExpense(BaseModel):
    action: Literal["update"]

    selector: RecordSelector

    updates: List[ExpenseFieldUpdate]


class DeleteExpense(BaseModel):
    action: str = "delete"
    selector: RecordSelector


from typing import Literal
from pydantic import BaseModel, Field


class QueryExpense(BaseModel):
    operation: Literal[
        "sum",
        "count",
        "list",
        "average",
        "max",
        "min",
    ]

    metric: Literal["amount"] = "amount"

    categories: list[str] = Field(default_factory=list)
    merchants: list[str] = Field(default_factory=list)
    payment_sources: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)

    filters: dict[str, str] = Field(default_factory=dict)
