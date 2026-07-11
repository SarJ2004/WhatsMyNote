"""LLM Factory functions."""

from langchain_groq import ChatGroq
from core.config import get_groq_api_key

def get_evaluator_llm() -> ChatGroq:
    """Get the evaluator LLM for complex tasks (Llama 3.3 70B)."""
    api_key = get_groq_api_key()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Please complete the setup.")
    return ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key)

def get_extractor_llm() -> ChatGroq:
    """Get the extractor LLM for simple extraction tasks (Llama 3.1 8B)."""
    api_key = get_groq_api_key()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Please complete the setup.")
    return ChatGroq(model="llama-3.1-8b-instant", api_key=api_key)
