import os
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.getenv("DATABASE_URL"), echo=False, future=True)

_SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(engine, "begin")
def _setup_rls(conn):
    user_id = os.environ.get("CURRENT_USER_ID")
    if user_id:
        conn.execute(sqlalchemy.text("set local role authenticated;"))
        conn.execute(sqlalchemy.text(f"set local request.jwt.claim.sub = '{user_id}';"))

def SessionLocal():
    return _SessionLocal()
