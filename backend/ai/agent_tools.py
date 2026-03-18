import logging
import re
from typing import Any

from langchain_core.tools import tool
from sentence_transformers import SentenceTransformer
from sqlmodel import Session

from ..schemas.scripture import ScriptureQuery
from ..db_session import engine
from ..services.sql_service import (
    get_translation,
    get_book,
    get_verse,
    get_verses,
    list_translations,
    get_semantic_similar_verses
)

logger = logging.getLogger("backend.ai.tools.agent_tools")

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

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


@tool(description="Given RAW bible verse text (not a reference or question),"
                  "find semantically similar verses across the Bible. "
                  "Use this AFTER you already have the verse text from scripture_lookup")
def semantic_search(verse_text: str) -> str:

    if re.match(r'^[\w\s]+\d+:\d+$', verse_text.strip()):
        return "Error: you must pass the actual verse text"

    try:
        embedding = embedding_model.encode(verse_text)
        embedding_list = embedding.tolist()
        logger.info(f"semantic_search embedding_list = {verse_text}")
        logger.info(f"tool_return semantic_search result = %s\n size of embedding = %s", _preview(embedding_list), embedding.shape[0])

        with Session(engine) as session:
            result_rows = get_semantic_similar_verses(embedding_list, session)

        formatted = "\n".join(
            f"({row.translation_shortname}) {row.book_name} {row.chapter_num}:{row.verse_num} - {row.verse_text}"
            for row in result_rows
        )
        result = f"Semantic search results:\n{formatted}"
        logger.info(result)
        return result
    except Exception:
        logger.exception("tool_error semantic_search query=%s", _preview(verse_text))
        raise


@tool(
    description="Look up scripture verses by translation, book, chapter, and verse number in the database. Returns raw verse text only."
)
def scripture_lookup(query: ScriptureQuery) -> str:
    query_translation = _norm_shortname(query.translation)

    logger.info(f"tool_return scripture_lookup query_translation = {query_translation}")

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
                f"({translation.translation_shortname}) {book.book_name} {v.chapter_num}:{v.verse_num}. {v.verse_text}"
                for v in verses
            )

    except Exception:
        logger.exception("tool_error scripture_lookup")
        raise


agent_tools = [available_translations, semantic_search, scripture_lookup]
