from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
evaluator_llm = ChatGroq(model="llama-3.1-8b-instant")
extractor_llm = ChatGroq(model="llama-3.1-8b-instant")
