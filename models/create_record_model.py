from pydantic import BaseModel
from datetime import date
from typing import Literal, List


class CreateRecordInput(BaseModel):
    person: str
    amount: int
    direction: Literal["lent", "borrowed"]
    expected_payback_by: date | None = None


class CreateRecord(BaseModel):
    action: Literal["create"]
    records: List[CreateRecordInput]
