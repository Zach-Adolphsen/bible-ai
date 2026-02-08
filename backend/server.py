from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from services.sql_service import get_book, get_translation, get_verse, get_verses
from services.sql_model import Translation

load_dotenv()
db_url = os.getenv("NEON_DB_URL")
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def create_db_and_tables():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"Health": "OK"}

@app.get("/bible/{translation}")
async def api_get_translation(translation: str, session: SessionDep) -> Translation:
    translation = get_translation(translation, session=session)

    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    return translation

@app.get("/bible/{translation}/{book}")
async def get_translation_book(translation: str, book: str, session: SessionDep):

    translation = get_translation(translation, session=session)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    book = get_book(book, session=session)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return {"translation": translation, "book": book}

@app.get("/bible/{translation}/{book}/{chapter:int}")
async def get_translation_book_chapter(translation: str, book: str, chapter: int, session: SessionDep):

    translation = get_translation(translation, session=session)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    book = get_book(book, session=session)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book_verses = get_verses(translation, book, chapter, session=session)
    if not book_verses:
        raise HTTPException(status_code=404, detail="Chapter not found")

    merged_dict = {
        "translation": translation,
        "book": book,
        "chapter": {}
    }

    for verse in book_verses:
        chapter_num: int = verse.chapter_num
        if chapter_num not in merged_dict["chapter"]:
            merged_dict["chapter"][chapter_num] = []
        merged_dict["chapter"][chapter_num].append({
            "verse_number": verse.verse_num,
            "verse_text": verse.verse_text
        })

    return merged_dict

@app.get("/bible/{translation}/{book}/{chapter:int}/{verse:int}")
async def get_translation_verse(translation: str, book: str, chapter: int, verse: int, session: SessionDep):

    translation = get_translation(translation, session=session)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    book = get_book(book, session=session)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book_verse = get_verse(translation, book, chapter, verse, session=session)
    if not book_verse:
        raise HTTPException(status_code=404, detail="Verse not found")

    merged_dict = {
        "translation": translation,
        "book": book,
        "chapter": {}
    }

    chapter_num: int = book_verse.chapter_num
    if chapter_num not in merged_dict["chapter"]:
        merged_dict["chapter"][chapter_num] = []
    merged_dict["chapter"][chapter_num].append({
            "verse_number": book_verse.verse_num,
            "verse_text": book_verse.verse_text
    })

    return merged_dict
