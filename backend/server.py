from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, Session, SQLModel, create_engine, select

db_url = "postgresql://neondb_owner:npg_jJUQf4qEGC7a@ep-polished-river-ahlioq3p-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Translation(SQLModel, table=True):
    __tablename__ = "translations"
    id : int | None = Field(default=None, primary_key=True)
    translation_shortname: str | None = Field(default=None)
    year_written_in: int | None = Field(default=None)
    translation_type: str | None = Field(default=None)

class Book(SQLModel, table=True):
    __tablename__ = "books"
    id: int | None = Field(default=None, primary_key=True)
    book_name: str | None = Field(default=None)
    testament: str | None = Field(default=None)

class Verse(SQLModel, table=True):
    __tablename__ = "verses"
    id: int | None = Field(default=None, primary_key=True)
    book_id: int | None = Field(default=None, foreign_key="books.id")
    translation_id: int | None = Field(default=None, foreign_key="translations.id")
    chapter_num: int | None = Field(default=None)
    verse_num: int | None = Field(default=None)
    verse_text: str | None = Field(default=None)

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
async def get_translation(translation: str, session: SessionDep) -> Translation:
    statement = select(Translation).where(Translation.translation_shortname == translation)
    translation = session.exec(statement).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    return translation

@app.get("/bible/{translation}/{book}")
async def get_translation_book(translation: str, book: str, session: SessionDep):
    statement = select(Translation).where(Translation.translation_shortname == translation)
    translation = session.exec(statement).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    statement = select(Book).where(Book.book_name == book)
    book = session.exec(statement).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return {"translation": translation, "book": book}

@app.get("/bible/{translation}/{book}/{chapter:int}")
async def get_translation_book_chapter(translation: str, book: str, chapter: int, session: SessionDep):

    statement = select(Translation).where(Translation.translation_shortname == translation)
    translation = session.exec(statement).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    statement = select(Book).where(Book.book_name == book)
    book = session.exec(statement).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    statement = select(Verse).where(Verse.book_id == book.id).where(Verse.chapter_num == chapter).order_by(Verse.verse_num)
    book_verses = session.exec(statement).all()
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
    statement = select(Translation).where(Translation.translation_shortname == translation)
    translation = session.exec(statement).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    statement = select(Book).where(Book.book_name == book)
    book = session.exec(statement).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book_verse = session.exec(
        select(Verse)
        .where(Verse.translation_id == translation.id)
        .where(Verse.book_id == book.id)
        .where(Verse.chapter_num == chapter)
        .where(Verse.verse_num == verse)
    ).first()

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
