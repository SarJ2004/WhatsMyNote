"""Record extraction models — central export point."""

from records.models.common import RecordSelector, TargetRecord, UpdateOperation

from records.models.expense import (
    CreateExpense, UpdateExpense, DeleteExpense, QueryExpense,
)
from records.models.income import (
    CreateIncome, UpdateIncome, DeleteIncome, QueryIncome,
)
from records.models.lending import (
    CreateLending, UpdateLending, DeleteLending, QueryLending,
)
from records.models.transfer import (
    CreateTransfer, UpdateTransfer, DeleteTransfer, QueryTransfer,
)
from records.models.account import (
    CreateAccount, UpdateAccount, DeleteAccount, QueryAccount,
)
from records.models.budget import (
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
