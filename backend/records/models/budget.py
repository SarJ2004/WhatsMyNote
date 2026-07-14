"""Budget extraction models."""

from datetime import date
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

from backend.records.models.common import RecordSelector, UpdateOperation, CleanStringModel


class BudgetInput(CleanStringModel):
    category: str
    amount: int
    period: str = "monthly"
    budget_date: date | None = None
    notes: str | None = None


class CreateBudget(BaseModel):
    action: Literal["create"]
    records: list[BudgetInput]


class BudgetField(str, Enum):
    CATEGORY = "category"
    AMOUNT = "amount"
    PERIOD = "period"
    BUDGET_DATE = "budget_date"
    NOTES = "notes"


class BudgetFieldUpdate(BaseModel):
    field: BudgetField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[str, int, float, date]


class UpdateBudget(BaseModel):
    action: Literal["update"]
    selector: RecordSelector
    updates: list[BudgetFieldUpdate] = Field(default_factory=list)


class DeleteBudget(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class QueryBudget(BaseModel):
    operation: Literal["sum", "count", "list", "average", "max", "min"]
    metric: Literal["amount"] = "amount"
    categories: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
