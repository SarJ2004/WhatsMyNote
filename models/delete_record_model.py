from pydantic import BaseModel
from models.selectors import RecordSelector


class DeleteRecord(BaseModel):
    action: str = "delete"
    selector: RecordSelector
