from pydantic import BaseModel, Field
from datetime import date
from enum import Enum
from typing import Literal, List, Union
from models.selectors import RecordSelector


class LendingInput(BaseModel):
    person: str
    amount: int
    direction: Literal["lent", "borrowed"]
    expected_payback_by: date | None = None


class CreateLending(BaseModel):
    action: Literal["create"]
    records: List[LendingInput]


class DeleteLending(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class UpdateOperation(str, Enum):
    SET = "set"
    ADD = "add"
    SUB = "subtract"
    MULTIPLY = "multiply"


class LendingField(str, Enum):
    PERSON = "person"
    AMOUNT = "amount"
    STATUS = "status"
    DIRECTION = "direction"
    EXPECTED_PAYBACK_BY = "expected_payback_by"


class FieldUpdate(BaseModel):
    field: LendingField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[
        str, int, float, date
    ]  # can be amount, person name, date, direction, status, etc.


class UpdateLending(BaseModel):
    action: str = "update"

    selector: RecordSelector

    updates: List[FieldUpdate]


class QueryLending(BaseModel):
    operation: Literal["sum", "count", "list", "difference", "net_balance", "list"]

    people: list[str] = Field(default_factory=list)
    metric: Literal["all", "lent", "borrowed", "outstanding"] = "all"
    filters: dict[str, str] = Field(default_factory=dict)
