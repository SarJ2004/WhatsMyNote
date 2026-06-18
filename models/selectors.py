from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TargetRecord(str, Enum):
    LAST = "last"
    PERSON = "person"


class RecordSelector(BaseModel):
    target: TargetRecord
    person: Optional[str] = None  # used when target is PERSON
