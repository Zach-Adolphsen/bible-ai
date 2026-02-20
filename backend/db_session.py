import os

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

db_url = os.getenv("NEON_DB_URL")
if not db_url:
    raise Exception("DATABASE URL IS NOT SET")

engine = create_engine(db_url)

def get_session():
    with Session(engine) as session:
        yield session