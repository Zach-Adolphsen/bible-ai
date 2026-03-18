from typing import Any, Sequence

from sqlmodel import select, Session

from sqlalchemy import text as sql_text
from ..schemas.models import Translation, Book, Verse


def get_semantic_similar_verses(embedding_list: list[float], session: Session, limit: int = 3) -> Sequence[Any]:
    sql = sql_text(
        """
        SELECT t.translation_shortname,
               b.book_name,
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
        LIMIT :limit
        OFFSET 1;
        """
    ).bindparams(embedding=str(embedding_list), limit=limit)

    return session.exec(sql).fetchall()


def get_translation(translation_shortname: str, session) -> Translation | None:
    stmt = (select(Translation)
            .where(Translation.translation_shortname == translation_shortname))

    return session.exec(stmt).first()


def list_translations(session: Session) -> Sequence[Any]:
    stmt = select(Translation)
    return session.exec(stmt).all()


def get_book(book: str, session) -> Book | None:
    stmt = select(Book).where(Book.book_name == book)

    return session.exec(stmt).first()


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
