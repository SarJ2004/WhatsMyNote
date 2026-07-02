from datetime import date
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

from models.selectors import RecordSelector


class IncomeInput(BaseModel):
    amount: int
    source: str
    income_date: date | None = None
    notes: str | None = None


class CreateIncome(BaseModel):
    action: Literal["create"]
    records: list[IncomeInput]


class DeleteIncome(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class UpdateOperation(str, Enum):
    SET = "set"
    ADD = "add"
    SUB = "subtract"
    MULTIPLY = "multiply"


class IncomeField(str, Enum):
    AMOUNT = "amount"
    SOURCE = "source"
    INCOME_DATE = "income_date"
    NOTES = "notes"


class IncomeFieldUpdate(BaseModel):
    field: IncomeField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[str, int, float, date]


class UpdateIncome(BaseModel):
    action: str = "update"
    selector: RecordSelector
    updates: list[IncomeFieldUpdate] = Field(default_factory=list)


class QueryIncome(BaseModel):
    operation: Literal["sum", "count", "list", "average", "max", "min"]
    metric: Literal["amount"] = "amount"
    sources: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)