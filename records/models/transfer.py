"""Transfer extraction models."""

from datetime import date
from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field

from records.models.common import RecordSelector, UpdateOperation


class TransferInput(BaseModel):
    source_account: str | None = None
    destination_account: str
    amount: int
    transfer_date: date | None = None
    notes: str | None = None


class CreateTransfer(BaseModel):
    action: Literal["create"]
    records: list[TransferInput]


class DeleteTransfer(BaseModel):
    action: str = "delete"
    selector: RecordSelector


class TransferField(str, Enum):
    SOURCE_ACCOUNT = "source_account"
    DESTINATION_ACCOUNT = "destination_account"
    AMOUNT = "amount"
    TRANSFER_DATE = "transfer_date"
    NOTES = "notes"


class TransferFieldUpdate(BaseModel):
    field: TransferField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[str, int, float, date]


class UpdateTransfer(BaseModel):
    action: str = "update"
    selector: RecordSelector
    updates: list[TransferFieldUpdate] = Field(default_factory=list)


class QueryTransfer(BaseModel):
    operation: Literal["sum", "count", "list", "average", "max", "min"]
    metric: Literal["amount"] = "amount"
    from_accounts: list[str] = Field(default_factory=list)
    to_accounts: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
