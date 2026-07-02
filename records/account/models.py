from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

from models.selectors import RecordSelector


class AccountInput(BaseModel):
    name: str
    opening_balance: int = 0
    currency: str | None = None
    notes: str | None = None


class CreateAccount(BaseModel):
    action: Literal["create"]
    records: list[AccountInput]


class UpdateOperation(str, Enum):
    SET = "set"
    ADD = "add"
    SUB = "subtract"
    MULTIPLY = "multiply"


class AccountField(str, Enum):
    NAME = "name"
    OPENING_BALANCE = "opening_balance"
    CURRENCY = "currency"
    NOTES = "notes"


class AccountFieldUpdate(BaseModel):
    field: AccountField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[str, int, float]


class UpdateAccount(BaseModel):
    action: Literal["update"]
    selector: RecordSelector
    updates: list[AccountFieldUpdate] = Field(default_factory=list)


class DeleteAccount(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class QueryAccount(BaseModel):
    operation: Literal["sum", "count", "list", "average", "max", "min", "balance"]
    metric: Literal["opening_balance", "balance"] = "balance"
    accounts: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
