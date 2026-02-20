from typing import Any, Sequence

from sqlmodel import select, Session

from .sql_model import Translation, Book, Verse


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
