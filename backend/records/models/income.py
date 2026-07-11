"""Income extraction models."""

from datetime import date
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

from backend.records.models.common import RecordSelector, UpdateOperation


class IncomeInput(BaseModel):
    amount: int
    source: str
    deposit_account: str | None = None
    income_date: date | None = None
    notes: str | None = None


class CreateIncome(BaseModel):
    action: Literal["create"]
    records: list[IncomeInput]


class DeleteIncome(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class IncomeField(str, Enum):
    AMOUNT = "amount"
    SOURCE = "source"
    DEPOSIT_ACCOUNT = "deposit_account"
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
    deposit_accounts: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
