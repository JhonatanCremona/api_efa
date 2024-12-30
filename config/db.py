from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv
import os

load_dotenv()
user = os.getenv("MY_SQL_USERNAME")
password = os.getenv("MY_SQL_PASSWORD")
port = os.getenv("MY_SQL_PORT")

engine = create_engine(f"mysql+pymysql://{user}:{password}@localhost:{port}/efadb")

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()