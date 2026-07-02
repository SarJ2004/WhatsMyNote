from datetime import date
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

from models.selectors import RecordSelector


class BudgetInput(BaseModel):
    category: str
    amount: int
    period: str = "monthly"
    budget_date: date | None = None
    notes: str | None = None


class CreateBudget(BaseModel):
    action: Literal["create"]
    records: list[BudgetInput]


class UpdateOperation(str, Enum):
    SET = "set"
    ADD = "add"
    SUB = "subtract"
    MULTIPLY = "multiply"


class BudgetField(str, Enum):
    CATEGORY = "category"
    AMOUNT = "amount"
    PERIOD = "period"
    NOTES = "notes"


class BudgetFieldUpdate(BaseModel):
    field: BudgetField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[str, int, float]


class UpdateBudget(BaseModel):
    action: Literal["update"]
    selector: RecordSelector
    updates: list[BudgetFieldUpdate] = Field(default_factory=list)


class DeleteBudget(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class QueryBudget(BaseModel):
    operation: Literal["sum", "count", "list", "average", "max", "min", "remaining", "variance"]
    metric: Literal["amount", "remaining", "variance"] = "remaining"
    categories: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
