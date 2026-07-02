from pydantic import BaseModel, Field
from records.lending.models import CreateLending
from records.lending.models import UpdateLending
from records.lending.models import DeleteLending
from records.lending.models import QueryLending
from records.expense.models import CreateExpense
from records.expense.models import UpdateExpense
from records.expense.models import DeleteExpense
from records.expense.models import QueryExpense
from records.account.models import CreateAccount
from records.account.models import UpdateAccount
from records.account.models import DeleteAccount
from records.account.models import QueryAccount
from records.income.models import CreateIncome
from records.income.models import UpdateIncome
from records.income.models import DeleteIncome
from records.income.models import QueryIncome
from records.transfer.models import CreateTransfer
from records.transfer.models import UpdateTransfer
from records.transfer.models import DeleteTransfer
from records.transfer.models import QueryTransfer
from records.budget.models import CreateBudget
from records.budget.models import UpdateBudget
from records.budget.models import DeleteBudget
from records.budget.models import QueryBudget

Extraction = (
    CreateLending
    | UpdateLending
    | DeleteLending
    | QueryLending
    | CreateExpense
    | UpdateExpense
    | DeleteExpense
    | QueryExpense
    | CreateAccount
    | UpdateAccount
    | DeleteAccount
    | QueryAccount
    | CreateIncome
    | UpdateIncome
    | DeleteIncome
    | QueryIncome
    | CreateTransfer
    | UpdateTransfer
    | DeleteTransfer
    | QueryTransfer
    | CreateBudget
    | UpdateBudget
    | DeleteBudget
    | QueryBudget
)


class State(BaseModel):
    raw_text: str
    intent: str | None = None
    extraction: Extraction | None = None
    record_type: str | None = None
    saved_record_ids: list[int] = Field(default_factory=list)
    analytics_mode: bool = False
    updated_record_id: int | None = None
    deleted_record_id: int | None = None
    query_result: object | None = None
    answer: str | None = None
    error: str | None = None
