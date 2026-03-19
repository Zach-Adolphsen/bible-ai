from typing import Any, Sequence

from sqlmodel import select, Session

from sqlalchemy import text as sql_text
from ..schemas.models import Translation, Book, Verse


def get_semantic_similar_verses(embedding_list: list[float], session: Session, limit: int = 20) -> Sequence[Any]:
    sql = sql_text(
        """
        SELECT t.translation_shortname,
               b.name,
               v.chapter_num,
               v.verse_num,
               v.verse_text
        FROM verses AS v
                 JOIN translations AS t
                      ON v.translation_id = t.id
                 JOIN books AS b
                      ON v.book_id = b.id
        WHERE t.translation_shortname = 'BSB'
        ORDER BY v.verse_embedding <=> CAST(:embedding AS vector)
        LIMIT :limit;
        """
    ).bindparams(embedding=str(embedding_list), limit=limit)

    return session.exec(sql).fetchall()


def keyword_search_verses(query: str, translation: Translation, session: Session, book: Book = None, limit: int = 10) -> Sequence[Any]:
    stmt = (
        select(
            Verse.chapter_num,
            Verse.verse_num,
            Verse.verse_text,
            Translation.translation_shortname,
            Book.name
        )
        .join(Translation, Verse.translation_id == Translation.id)
        .join(Book, Verse.book_id == Book.id)
        .where(Verse.translation_id == translation.id)
        .where(Verse.verse_text.ilike(f"%{query}%"))
        .limit(limit)
    )

    if book:
        stmt = stmt.where(Verse.book_id == book.id)

    return session.exec(stmt).all()


def get_translation(translation_shortname: str, session) -> Translation | None:
    stmt = (select(Translation)
            .where(Translation.translation_shortname == translation_shortname))

    return session.exec(stmt).first()


def list_translations(session: Session) -> Sequence[Any]:
    stmt = select(Translation)
    return session.exec(stmt).all()


def get_book(book: str, session) -> Book | None:
    stmt = select(Book).where(Book.name == book)

    return session.exec(stmt).first()

def get_books(session) -> list[Book]:
    stmt = select(Book)

    return session.exec(stmt).all()

def get_book_chapters(translation: Translation, book: Book, session: Session):
    stmt = (select(Verse.chapter_num)
         .where(Verse.translation_id == translation.id)
         .where(Verse.book_id == book.id)
         .group_by(Verse.chapter_num)
         .order_by(Verse.chapter_num)
         )
    
    return session.exec(stmt).all()


def get_verses(translation: Translation, book: Book, chapter: int, session) -> list[Verse]:
    stmt = (select(Verse)
            .where(Verse.translation_id == translation.id)
            .where(Verse.book_id == book.id)
            .where(Verse.chapter_num == chapter)
            .order_by(Verse.verse_num))

    return session.exec(stmt).all()


def get_verse(translation: Translation, book: Book, chapter: int, verse: int, session) -> Verse | None:
    stmt = (select(Verse)
            .where(Verse.translation_id == translation.id)
            .where(Verse.book_id == book.id)
            .where(Verse.chapter_num == chapter)
            .where(Verse.verse_num == verse))

    return session.exec(stmt).first()
