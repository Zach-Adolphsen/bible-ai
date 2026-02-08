from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session
from .schema import ScriptureQuery
from backend.server import engine
from backend.services.sql_service import get_translation, get_book, get_verse, get_verses

def fetch_scripture(query: ScriptureQuery) -> str:
    with Session(engine) as session:
        translation = get_translation(query.translation, session)
        if not translation:
            return f"Translation '{query.translation}' not found."

        book = get_book(query.book, session)
        if not book:
            return f"Book '{query.book}' not found."

        if query.verse is not None:
            verse = get_verse(
                translation,
                book,
                query.chapter,
                query.verse,
                session
            )
            if not verse:
                return "Verse not found."

            return f"{book.book_name} {query.chapter}:{query.verse} ({translation.translation_shortname})\n{verse.text}"

        verses = get_verses(
            translation,
            book,
            query.chapter,
            session
        )

        if not verses:
            return "Chapter not found."

        return "\n".join(
            f"{v.verse_num}. {v.text}" for v in verses
        )

scripture_tool = StructuredTool.from_function(
    name="fetch_scripture",
    description=(
        "Retrieve Bible verse by translation, book, chapter, and optional verse number."
    ),
    func=fetch_scripture,
    args_schema=ScriptureQuery,
)
