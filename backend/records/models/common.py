"""Shared model components used across all record types."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, model_validator


class CleanStringModel(BaseModel):
    @model_validator(mode='before')
    @classmethod
    def clean_null_strings(cls, data: dict) -> dict:
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    if value.strip().lower() in ["null", "none", "n/a", ""]:
                        data[key] = None
        return data


class TargetRecord(str, Enum):
    LAST = "last"
    PERSON = "person"
    ACCOUNT = "account"
    SOURCE = "source"
    CATEGORY = "category"
    ID = "id"


class RecordSelector(BaseModel):
    target: TargetRecord
    person: Optional[str] = None
    account: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    record_id: Optional[int] = None


class UpdateOperation(str, Enum):
    SET = "set"
    ADD = "add"
    SUB = "subtract"
    MULTIPLY = "multiply"
