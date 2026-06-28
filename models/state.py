from pydantic import BaseModel, Field
from records.lending.models import CreateLending
from records.lending.models import UpdateLending
from records.lending.models import DeleteLending
from records.lending.models import QueryLending
from records.expense.models import CreateExpense

Extraction = (
    CreateLending | UpdateLending | DeleteLending | QueryLending | CreateExpense
)


class State(BaseModel):
    raw_text: str
    intent: str | None = None
    extraction: Extraction | None = None
    record_type: str | None = None
    saved_record_ids: list[int] = Field(default_factory=list)
    updated_record_id: int | None = None
    deleted_record_id: int | None = None
    query_result: object | None = None
    answer: str | None = None
    error: str | None = None
