from sqlmodel import select
from .sql_model import Translation, Book, Verse


def get_translation(translation_shortname: str, session) -> Translation | None:
    stmt = (select(Translation)
            .where(Translation.translation_shortname == translation_shortname))

    return session.exec(stmt).first()

def get_book(book: str, session) -> Book | None:
    statement = select(Book).where(Book.book_name == book)

    return session.exec(statement).first()


def get_verses(translation: Translation, book: Book, chapter: int, session) -> list[Verse]:

    statement = (select(Verse)
                 .where(Verse.translation_id == translation.id)
                 .where(Verse.book_id == book.id)
                 .where(Verse.chapter_num == chapter)
                 .order_by(Verse.verse_num))

    return session.exec(statement).all()


def get_verse(translation: Translation, book: Book, chapter: int, verse: int, session) -> Verse | None:

    statement = (select(Verse)
                 .where(Verse.translation_id == translation.id)
                 .where(Verse.book_id == book.id)
                 .where(Verse.chapter_num == chapter)
                 .where(Verse.verse_num == verse))

    return session.exec(statement).first()
