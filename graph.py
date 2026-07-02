from langgraph.graph import START, END, StateGraph
from pprint import pprint
from models.state import State

from nodes.intent_classifier import (
    intent_evaluator,
    record_type_evaluator,
    intent_router,
    record_type_router,
)
from nodes.response_formatter import response_formatter

# Lending
from records.lending.extractor import (
    create_extractor as create_lending_extractor,
    update_extractor as update_lending_extractor,
    delete_extractor as delete_lending_extractor,
    query_extractor as lending_query_extractor,
)

from records.lending.saver import record_saver as lending_saver
from records.lending.updater import record_updater as lending_updater
from records.lending.deleter import record_deleter as lending_deleter
from records.lending.query_executor import (
    query_executor as lending_query_executor,
)

# Expense
from records.expense.extractor import (
    create_extractor as create_expense_extractor,
    update_extractor as update_expense_extractor,
    delete_extractor as delete_expense_extractor,
    query_extractor as expense_query_extractor,
)
from records.expense.saver import record_saver as expense_saver
from records.expense.updater import record_updater as expense_updater
from records.expense.deleter import record_deleter as expense_deleter
from records.expense.query_executor import (
    query_executor as expense_query_executor,
)

# Income
from records.income.extractor import (
    create_extractor as create_income_extractor,
    update_extractor as update_income_extractor,
    delete_extractor as delete_income_extractor,
    query_extractor as income_query_extractor,
)
from records.income.saver import record_saver as income_saver
from records.income.updater import record_updater as income_updater
from records.income.deleter import record_deleter as income_deleter
from records.income.query_executor import (
    query_executor as income_query_executor,
)

# Transfer
from records.transfer.extractor import (
    create_extractor as create_transfer_extractor,
    update_extractor as update_transfer_extractor,
    delete_extractor as delete_transfer_extractor,
    query_extractor as transfer_query_extractor,
)
from records.transfer.saver import record_saver as transfer_saver
from records.transfer.updater import record_updater as transfer_updater
from records.transfer.deleter import record_deleter as transfer_deleter
from records.transfer.query_executor import (
    query_executor as transfer_query_executor,
)

graph = StateGraph(State)

# --------------------------------------------------
# Intent
# --------------------------------------------------

graph.add_node("intent_evaluator", intent_evaluator)
graph.add_node(
    "record_type_evaluator",
    record_type_evaluator,
)

# --------------------------------------------------
# Lending
# --------------------------------------------------

graph.add_node(
    "create_lending_extractor",
    create_lending_extractor,
)

graph.add_node(
    "update_lending_extractor",
    update_lending_extractor,
)

graph.add_node(
    "delete_lending_extractor",
    delete_lending_extractor,
)

graph.add_node(
    "lending_query_extractor",
    lending_query_extractor,
)

graph.add_node(
    "lending_saver",
    lending_saver,
)

graph.add_node(
    "lending_updater",
    lending_updater,
)

graph.add_node(
    "lending_deleter",
    lending_deleter,
)

graph.add_node(
    "lending_query_executor",
    lending_query_executor,
)

# --------------------------------------------------
# Expense
# --------------------------------------------------

graph.add_node(
    "create_expense_extractor",
    create_expense_extractor,
)

graph.add_node(
    "update_expense_extractor",
    update_expense_extractor,
)

graph.add_node(
    "delete_expense_extractor",
    delete_expense_extractor,
)

graph.add_node(
    "expense_query_extractor",
    expense_query_extractor,
)
graph.add_node(
    "expense_saver",
    expense_saver,
)

graph.add_node(
    "expense_updater",
    expense_updater,
)

graph.add_node(
    "expense_deleter",
    expense_deleter,
)

graph.add_node(
    "expense_query_executor",
    expense_query_executor,
)

# --------------------------------------------------
# Income
# --------------------------------------------------

graph.add_node(
    "create_income_extractor",
    create_income_extractor,
)

graph.add_node(
    "update_income_extractor",
    update_income_extractor,
)

graph.add_node(
    "delete_income_extractor",
    delete_income_extractor,
)

graph.add_node(
    "income_query_extractor",
    income_query_extractor,
)

graph.add_node(
    "income_saver",
    income_saver,
)

graph.add_node(
    "income_updater",
    income_updater,
)

graph.add_node(
    "income_deleter",
    income_deleter,
)

graph.add_node(
    "income_query_executor",
    income_query_executor,
)

# --------------------------------------------------
# Transfer
# --------------------------------------------------

graph.add_node(
    "create_transfer_extractor",
    create_transfer_extractor,
)

graph.add_node(
    "update_transfer_extractor",
    update_transfer_extractor,
)

graph.add_node(
    "delete_transfer_extractor",
    delete_transfer_extractor,
)

graph.add_node(
    "transfer_query_extractor",
    transfer_query_extractor,
)

graph.add_node(
    "transfer_saver",
    transfer_saver,
)

graph.add_node(
    "transfer_updater",
    transfer_updater,
)

graph.add_node(
    "transfer_deleter",
    transfer_deleter,
)

graph.add_node(
    "transfer_query_executor",
    transfer_query_executor,
)


# --------------------------------------------------
# Shared
# --------------------------------------------------

graph.add_node(
    "response_formatter",
    response_formatter,
)

# --------------------------------------------------
# Edges
# --------------------------------------------------

graph.add_edge(
    START,
    "intent_evaluator",
)

graph.add_conditional_edges(
    "intent_evaluator",
    intent_router,
    {
        "record_type_evaluator": "record_type_evaluator",
        "END": END,
    },
)

graph.add_conditional_edges(
    "record_type_evaluator",
    record_type_router,
    {
        "create_lending_extractor": "create_lending_extractor",
        "update_lending_extractor": "update_lending_extractor",
        "delete_lending_extractor": "delete_lending_extractor",
        "create_expense_extractor": "create_expense_extractor",
        "update_expense_extractor": "update_expense_extractor",
        "delete_expense_extractor": "delete_expense_extractor",
        "lending_query_extractor": "lending_query_extractor",
        "expense_query_extractor": "expense_query_extractor",
        "create_income_extractor": "create_income_extractor",
        "update_income_extractor": "update_income_extractor",
        "delete_income_extractor": "delete_income_extractor",
        "income_query_extractor": "income_query_extractor",
        "create_transfer_extractor": "create_transfer_extractor",
        "update_transfer_extractor": "update_transfer_extractor",
        "delete_transfer_extractor": "delete_transfer_extractor",
        "transfer_query_extractor": "transfer_query_extractor",
        "END": END,
    },
)

# Lending

graph.add_edge(
    "create_lending_extractor",
    "lending_saver",
)

graph.add_edge(
    "update_lending_extractor",
    "lending_updater",
)

graph.add_edge(
    "delete_lending_extractor",
    "lending_deleter",
)

graph.add_edge(
    "lending_query_extractor",
    "lending_query_executor",
)

graph.add_edge(
    "lending_saver",
    "response_formatter",
)

graph.add_edge(
    "lending_updater",
    "response_formatter",
)

graph.add_edge(
    "lending_deleter",
    "response_formatter",
)

graph.add_edge(
    "lending_query_executor",
    "response_formatter",
)


# Expense

graph.add_edge(
    "create_expense_extractor",
    "expense_saver",
)

graph.add_edge(
    "update_expense_extractor",
    "expense_updater",
)

graph.add_edge(
    "delete_expense_extractor",
    "expense_deleter",
)

graph.add_edge(
    "expense_query_extractor",
    "expense_query_executor",
)

graph.add_edge(
    "expense_saver",
    "response_formatter",
)

graph.add_edge(
    "expense_updater",
    "response_formatter",
)

graph.add_edge(
    "expense_deleter",
    "response_formatter",
)

graph.add_edge(
    "expense_query_executor",
    "response_formatter",
)


# Income

graph.add_edge(
    "create_income_extractor",
    "income_saver",
)

graph.add_edge(
    "update_income_extractor",
    "income_updater",
)

graph.add_edge(
    "delete_income_extractor",
    "income_deleter",
)

graph.add_edge(
    "income_query_extractor",
    "income_query_executor",
)

graph.add_edge(
    "income_saver",
    "response_formatter",
)

graph.add_edge(
    "income_updater",
    "response_formatter",
)

graph.add_edge(
    "income_deleter",
    "response_formatter",
)

graph.add_edge(
    "income_query_executor",
    "response_formatter",
)


# Transfer

graph.add_edge(
    "create_transfer_extractor",
    "transfer_saver",
)

graph.add_edge(
    "update_transfer_extractor",
    "transfer_updater",
)

graph.add_edge(
    "delete_transfer_extractor",
    "transfer_deleter",
)

graph.add_edge(
    "transfer_query_extractor",
    "transfer_query_executor",
)

graph.add_edge(
    "transfer_saver",
    "response_formatter",
)

graph.add_edge(
    "transfer_updater",
    "response_formatter",
)

graph.add_edge(
    "transfer_deleter",
    "response_formatter",
)

graph.add_edge(
    "transfer_query_executor",
    "response_formatter",
)

graph.add_edge(
    "response_formatter",
    END,
)

compiled_graph = graph.compile()

if __name__ == "__main__":
    message = input("Enter your message: ")

    result = compiled_graph.invoke(
        {
            "raw_text": message,
        }
    )

    pprint(result)
