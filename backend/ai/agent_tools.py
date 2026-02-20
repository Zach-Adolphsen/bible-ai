import logging
from typing import Any

from langchain_core.tools import tool
from sqlmodel import Session

from backend.ai.schema import ScriptureQuery
from backend.db_session import engine
from backend.services.sql_service import get_translation, get_book, get_verse, get_verses, list_translations

logger = logging.getLogger("backend.ai.tools.agent_tools")


def _preview(value: Any, limit: int = 200) -> str:
    """Return a safe, short preview string for logs."""
    try:
        s = str(value)
    except Exception:
        return "<unprintable>"
    if len(s) > limit:
        return s[:limit] + "...(truncated)"
    return s


def _norm_shortname(s: Any) -> str:
    """Normalize translation shortname for DB lookup (e.g., 'niv' -> 'NIV')."""
    if s is None:
        return ""
    return str(s).strip().upper()


@tool(description="List the Bible translations that are available in the database (shortnames like KJV, BSB).")
def available_translations() -> str:
    logger.info("tool_called available_translations")
    try:
        with Session(engine) as session:
            translations = list_translations(session)
            shortnames = sorted(
                {t.translation_shortname for t in translations if getattr(t, "translation_shortname", None)}
            )
        result = ", ".join(shortnames) if shortnames else "(none found)"
        logger.info(
            "tool_return available_translations result = %s",
            _preview(result),
        )
        return result
    except Exception:
        logger.exception("tool_error available_translations")
        raise


@tool(description="Search for semantically relevant Bible verses.")
def semantic_search(query: str) -> str:
    try:
        result = f"Semantic search results for: {query}"
        return result
    except Exception:
        logger.exception("tool_error semantic_search query=%s", _preview(query))
        raise


@tool(
    description="Look up scripture verses by translation, book, chapter, and verse number in the database. Returns raw verse text only."
)
def scripture_lookup(query: ScriptureQuery) -> str:

    query_translation = _norm_shortname(query.translation)

    try:
        with Session(engine) as session:

            translation = get_translation(query_translation, session)
            if not translation:
                return "Translation not found."

            book = get_book(query.book, session)
            if not book:
                return "Book not found."

            # Single verse
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

                return verse.verse_text

            # Entire chapter
            verses = get_verses(
                translation,
                book,
                query.chapter,
                session
            )

            if not verses:
                return "Chapter not found."

            return "\n".join(
                f"({translation.translation_shortname}) {book.book_name} {v.chapter_num}:{v.verse_num}. {v.text}"
                for v in verses
            )

    except Exception:
        logger.exception("tool_error scripture_lookup")
        raise


agent_tools = [available_translations, semantic_search, scripture_lookup]

