import os
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True  
)

def get_conn():
    try:
        return engine.connect()
    except SQLAlchemyError as e:
        print(f"DB Connection Error: {e}")
        raise