import os
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
from fastapi.encoders import jsonable_encoder

app = FastAPI()

def setup_backend_env():
    # Setup config loads env vars first
    from backend.core.config import setup_backend_env as _setup_env
    _setup_env()

setup_backend_env()

# Initialize global Supabase client once
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if url and key:
    _supabase_client: Client = create_client(url, key)
else:
    _supabase_client = None

def verify_token(authorization: str = Header(None), x_groq_api_key: str = Header(None)) -> str:
    if _supabase_client is None:
        raise HTTPException(status_code=500, detail="Backend missing Supabase config")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    
    if x_groq_api_key:
        os.environ["GROQ_API_KEY"] = x_groq_api_key
        
    res = _supabase_client.auth.get_user(token)
    if not res or not res.user:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    os.environ["CURRENT_USER_ID"] = res.user.id
    return res.user.id

class ChatRequest(BaseModel):
    message: str
    state: dict = {}

@app.post("/chat")
def chat(req: ChatRequest, user_id: str = Depends(verify_token)):
    from backend.core.graph import compiled_graph
    
    app_state = req.state
    app_state["raw_text"] = req.message
    
    try:
        new_state = compiled_graph.invoke(app_state)
        
        if os.environ.get("ENV") != "dev":
            new_state.pop("analytics_sql", None)
            new_state.pop("analytics_review", None)
            
    except Exception as e:
        if os.environ.get("ENV") == "dev":
            raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
        
    return {"state": jsonable_encoder(new_state)}

class SetupRequest(BaseModel):
    accounts: list[dict]
    budgets: list[dict]
    default_account_index: Optional[int] = None

@app.post("/setup")
def setup(req: SetupRequest, user_id: str = Depends(verify_token)):
    from backend.db.config import SessionLocal
    from backend.db.schema import AccountRecord, BaseRecord, BudgetRecord, RecordType
    from backend.records.account_utils import set_default_account_name
    
    db = SessionLocal()
    try:
        for idx, item in enumerate(req.accounts):
            base_record = BaseRecord(
                record_type=RecordType.ACCOUNT, raw_text="Initial account setup"
            )
            base_record.account = AccountRecord(
                name=item["name"],
                is_default=(idx == req.default_account_index),
                opening_balance=item.get("opening_balance", 0),
                current_balance=item.get("opening_balance", 0),
                currency=item.get("currency"),
                notes=item.get("notes"),
            )
            db.add(base_record)
            
        for item in req.budgets:
            base_record = BaseRecord(
                record_type=RecordType.BUDGET, raw_text="Initial budget setup"
            )
            base_record.budget = BudgetRecord(
                category=item["category"],
                amount=item["amount"],
                period=item.get("period", "monthly"),
                budget_date=item.get("budget_date"),
                notes=item.get("notes"),
            )
            db.add(base_record)
            
        db.commit()
        
        if req.accounts and req.default_account_index is not None and req.default_account_index < len(req.accounts):
            set_default_account_name(db, req.accounts[req.default_account_index]["name"])
            db.commit()
            
    except Exception as e:
        db.rollback()
        if os.environ.get("ENV") == "dev":
            raise HTTPException(status_code=500, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        db.close()
        
    return {"status": "success"}

@app.get("/setup/status")
def setup_status(user_id: str = Depends(verify_token)):
    from backend.db.config import SessionLocal
    from backend.db.schema import AccountRecord, BudgetRecord
    from backend.records.account_utils import get_default_account_name
    db = SessionLocal()
    try:
        account_count = db.query(AccountRecord).count()
        budget_count = db.query(BudgetRecord).count()
        default_account = get_default_account_name(db)
        return {
            "account_count": account_count,
            "budget_count": budget_count,
            "default_account": default_account
        }
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {
        "service": "WhatsMyNote API",
        "status": "online",
        "message": "The backend is running successfully!"
    }
