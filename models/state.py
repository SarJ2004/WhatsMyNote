from pydantic import BaseModel, Field
from models.create_record_model import CreateRecord
from models.update_record_model import UpdateRecord
from models.delete_record_model import DeleteRecord


class State(BaseModel):
    raw_text: str
    intent: str | None = None
    extraction: CreateRecord | UpdateRecord | DeleteRecord | None = None
    saved_record_ids: list[int] = Field(default_factory=list)
    updated_record_id: int | None = None
    deleted_record_id: int | None = None
    response: str | None = None
    answer: str | None = None
    error: str | None = None
