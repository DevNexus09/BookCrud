import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

"""
Database connection. Set DATABASE_URL to use another database, e.g.
  mysql+pymysql://root:pass@localhost:3306/books
  postgresql+psycopg2://user:pass@localhost:5432/books
Defaults to a SQLite file next to this module, independent of the working directory.
"""

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{Path(__file__).parent / 'database.db'}")

# SQLite connections are per-thread by default; FastAPI runs sync handlers in a threadpool.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
