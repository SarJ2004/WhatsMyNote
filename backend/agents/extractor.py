"""Generic extractor — loads the right prompt and model for any (intent, record_type) pair."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llms import get_extractor_llm
from backend.records.models import MODEL_REGISTRY
from backend.records.search import search_recent_records


def _load_prompt(intent: str, record_type: str) -> str:
    """Load the prompt file for a given intent and record type."""
    prompt_path = Path(__file__).parent / "prompts" / intent / f"{record_type}.md"
    if not prompt_path.exists():
        return f"Extract the {intent} details for a {record_type} record. Return valid JSON."
    return prompt_path.read_text()


def _dynamic_context() -> str:
    from backend.db.config import SessionLocal
    from backend.db.schema import AccountRecord, ExpenseRecord, BudgetRecord, IncomeRecord
    from sqlalchemy import func
    
    accounts, categories, income_sources = [], [], []
    try:
        db = SessionLocal()
        accounts = [a.name for a in db.query(AccountRecord).all() if a.name]
        
        expense_cats = [
            row[0] for row in db.query(ExpenseRecord.category)
            .group_by(ExpenseRecord.category)
            .order_by(func.count(ExpenseRecord.category).desc())
            .limit(10).all() if row[0]
        ]
        budget_cats = [row[0] for row in db.query(BudgetRecord.category).distinct().all() if row[0]]
        categories = list(set(expense_cats + budget_cats))
        
        income_sources = [
            row[0] for row in db.query(IncomeRecord.source)
            .group_by(IncomeRecord.source)
            .order_by(func.count(IncomeRecord.source).desc())
            .limit(10).all() if row[0]
        ]
    except Exception:
        pass
    finally:
        db.close()
        
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    
    context = (
        f"Today's date is {today.isoformat()}. "
        f"Yesterday was {yesterday}. "
        "If no date is mentioned by the user, do not set a date field.\n\n"
    )
    
    STANDARD_EXPENSE_CATEGORIES = [
        "Overall", "Housing", "Food & Dining", "Groceries", "Utilities", "Transportation", 
        "Healthcare", "Personal Care", "Entertainment", "Education", "Shopping", 
        "Travel", "Debt & Loans", "Savings & Investments", "Gifts & Donations", "Others"
    ]
    
    STANDARD_INCOME_SOURCES = [
        "Salary", "Freelance & Business", "Dividends & Investments", "Interest", 
        "Refunds", "Gifts", "Others"
    ]
    
    STANDARD_ACCOUNTS = [
        "Cash", "Bank Account", "Credit Card", "Digital Wallet"
    ]
    
    context += f"STANDARD EXPENSE/BUDGET CATEGORIES: {', '.join(STANDARD_EXPENSE_CATEGORIES)}\n"
    context += f"STANDARD INCOME SOURCES: {', '.join(STANDARD_INCOME_SOURCES)}\n"
    context += f"STANDARD ACCOUNTS: {', '.join(STANDARD_ACCOUNTS)}\n\n"
    
    if accounts:
        context += f"User's Existing Accounts: {', '.join(accounts)}\n"
    if categories:
        context += f"User's Custom Categories: {', '.join(categories)}\n"
    if income_sources:
        context += f"User's Custom Income Sources: {', '.join(income_sources)}\n"
        
    context += (
        "\nIMPORTANT EXTRACTION RULES:\n"
        "1. Prioritize 'User's Custom Categories' and 'User's Custom Income Sources' over STANDARD categories.\n"
        "2. If a user's expense or budget semantically matches a custom category (e.g., user has 'Food' and standard is 'Food & Dining'), you MUST output the exact name of the custom category.\n"
        "3. Only use standard categories or invent new ones if NO custom category is a good match.\n"
    )
        
    return context + "\n"


def extractor(state):
    """Generic extraction node — dispatches based on state.get("intent") + state.get("record_type")."""
    intent = state.get("intent")
    record_type = state.get("record_type")

    if not intent or not record_type:
        return {"error": "Missing intent or record type for extraction."}

    model_cls = MODEL_REGISTRY.get((intent, record_type))
    if model_cls is None:
        return {"error": f"No model registered for ({intent}, {record_type})."}

    prompt = _load_prompt(intent, record_type)

    messages = [
        SystemMessage(content=_dynamic_context() + prompt),
        HumanMessage(content=state.get("raw_text")),
    ]

    try:
        # Use native LangChain guardrails to enforce the schema on the LLM level
        llm_with_tools = get_extractor_llm().with_structured_output(model_cls, method="json_mode")
        validated = llm_with_tools.invoke(messages)

        return {"extraction": validated.model_dump(mode="json")}

    except Exception as e:
        # For delete/update with ambiguous targets, offer HITL search
        if intent in ("delete", "update"):
            results = search_recent_records(record_type)
            if results:
                return {
                    "search_results": results,
                    "awaiting_selection": True,
                    "answer": f"I couldn't determine which {record_type} to {intent}. Please select from the list below.",
                }
            else:
                return {"error": f"You don't have any {record_type} records to {intent}."}
        return {"error": f"Failed to extract details: {e}"}


def extractor_router(state):
    """Route after extraction — send creates to saver, updates/deletes to confirmation."""
    if state.get("error"):
        return "response_formatter"

    if state.get("awaiting_selection"):
        return "response_formatter"

    intent = state.get("intent")

    if intent == "create":
        return "record_saver"
    elif intent in ("update", "delete"):
        return "request_confirmation"
    elif intent == "query":
        return "query_executor"

    return "response_formatter"
