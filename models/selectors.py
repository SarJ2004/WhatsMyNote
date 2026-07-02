from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TargetRecord(str, Enum):
    LAST = "last"
    PERSON = "person"
    ACCOUNT = "account"
    SOURCE = "source"
    CATEGORY = "category"


class RecordSelector(BaseModel):
    target: TargetRecord
    person: Optional[str] = None  # used when target is PERSON
    account: Optional[str] = None  # used when target is ACCOUNT
    source: Optional[str] = None  # used when target is SOURCE
    category: Optional[str] = None  # used when target is CATEGORY
