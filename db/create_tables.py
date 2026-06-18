from db.models import Base
from db.config import engine

Base.metadata.create_all(bind=engine)
