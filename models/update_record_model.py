from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import date
from models.selectors import RecordSelector


class UpdateOperation(str, Enum):
    SET = "set"
    ADD = "add"
    SUB = "subtract"
    MULTIPLY = "multiply"


class RecordField(str, Enum):
    PERSON = "person"
    AMOUNT = "amount"
    STATUS = "status"
    DIRECTION = "direction"
    EXPECTED_PAYBACK_BY = "expected_payback_by"


class FieldUpdate(BaseModel):
    field: RecordField
    operation: UpdateOperation = UpdateOperation.SET
    value: Union[
        str, int, float, date
    ]  # can be amount, person name, date, direction, status, etc.


class UpdateRecord(BaseModel):
    action: str = "update"

    selector: RecordSelector

    updates: List[FieldUpdate]
