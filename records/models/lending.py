"""Lending extraction models."""

from datetime import date
from enum import Enum
from typing import Literal, List, Union

from pydantic import BaseModel, Field

from records.models.common import RecordSelector, UpdateOperation


class LendingInput(BaseModel):
    person: str
    account: str | None = None
    amount: int
    direction: Literal["lent", "borrowed"]
    expected_payback_by: date | None = None


class CreateLending(BaseModel):
    action: Literal["create"]
    records: List[LendingInput]


class DeleteLending(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class LendingField(str, Enum):
    PERSON = "person"
    ACCOUNT = "account"
    AMOUNT = "amount"
    DIRECTION = "direction"
    EXPECTED_PAYBACK_BY = "expected_payback_by"


class LendingFieldUpdate(BaseModel):
    field: LendingField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[str, int, float, date]


class UpdateLending(BaseModel):
    action: str = "update"
    selector: RecordSelector
    updates: List[LendingFieldUpdate] = Field(default_factory=list)


class QueryLending(BaseModel):
    operation: Literal["sum", "count", "list", "difference", "net_balance"]
    people: list[str] = Field(default_factory=list)
    metric: Literal["all", "lent", "borrowed", "outstanding"] = "all"
    filters: dict[str, str] = Field(default_factory=dict)
