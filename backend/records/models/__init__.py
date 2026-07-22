"""Record extraction models — central export point."""

from backend.records.models.common import RecordSelector, TargetRecord, UpdateOperation

__all__ = [
    "RecordSelector",
    "TargetRecord",
    "UpdateOperation",
]

from backend.records.models.expense import (
    CreateExpense, UpdateExpense, DeleteExpense, QueryExpense,
)
from backend.records.models.income import (
    CreateIncome, UpdateIncome, DeleteIncome, QueryIncome,
)
from backend.records.models.lending import (
    CreateLending, UpdateLending, DeleteLending, QueryLending,
)
from backend.records.models.transfer import (
    CreateTransfer, UpdateTransfer, DeleteTransfer, QueryTransfer,
)
from backend.records.models.account import (
    CreateAccount, UpdateAccount, DeleteAccount, QueryAccount,
)
from backend.records.models.budget import (
    CreateBudget, UpdateBudget, DeleteBudget, QueryBudget,
)

# Maps (intent, record_type) → Pydantic model class
MODEL_REGISTRY: dict[tuple[str, str], type] = {
    ("create", "expense"): CreateExpense,
    ("update", "expense"): UpdateExpense,
    ("delete", "expense"): DeleteExpense,
    ("query", "expense"): QueryExpense,

    ("create", "income"): CreateIncome,
    ("update", "income"): UpdateIncome,
    ("delete", "income"): DeleteIncome,
    ("query", "income"): QueryIncome,

    ("create", "lending"): CreateLending,
    ("update", "lending"): UpdateLending,
    ("delete", "lending"): DeleteLending,
    ("query", "lending"): QueryLending,

    ("create", "transfer"): CreateTransfer,
    ("update", "transfer"): UpdateTransfer,
    ("delete", "transfer"): DeleteTransfer,
    ("query", "transfer"): QueryTransfer,

    ("create", "account"): CreateAccount,
    ("update", "account"): UpdateAccount,
    ("delete", "account"): DeleteAccount,
    ("query", "account"): QueryAccount,

    ("create", "budget"): CreateBudget,
    ("update", "budget"): UpdateBudget,
    ("delete", "budget"): DeleteBudget,
    ("query", "budget"): QueryBudget,
}
