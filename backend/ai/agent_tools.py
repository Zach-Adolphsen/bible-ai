import logging
import time
from typing import Any

from langchain_core.tools import tool
from sqlmodel import Session

from backend.db_session import engine
from backend.services.sql_service import get_translation, get_book, get_verse, get_verses, list_translations
from .schema import ScriptureQuery

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
    started = time.perf_counter()
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


# @tool(description="Look up a Bible verse by reference (e.g., John 3:16)")
# def verse_lookup(reference: str) -> str:
#     logger.info("tool_called verse_lookup reference=%s", _preview(reference))
#     try:
#         result = f"Lookup result for {reference}"
#         logger.info(
#             "tool_return verse_lookup result = %s",
#             _preview(result),
#         )
#         return result
#     except Exception:
#         logger.exception("tool_error verse_lookup reference=%s", _preview(reference))
#         raise


@tool(description="Search for semantically relevant Bible verses.")
def semantic_search(query: str) -> str:
    logger.info("tool_called semantic_search query=%s", _preview(query))
    try:
        result = f"Semantic search results for: {query}"
        logger.info(
            "tool_return semantic_search result = %s",
            result,
        )
        return result
    except Exception:
        logger.exception("tool_error semantic_search query=%s", _preview(query))
        raise


# @tool(description="Expand a verse reference to include surrounding verses.")
# def expand_context(reference: str) -> str:
#     logger.info("tool_called expand_context reference=%s", _preview(reference))
#     try:
#         result = f"Expanded context for {reference}"
#         logger.info(
#             "tool_return expand_context result = %s",
#             _preview(result),
#         )
#         return result
#     except Exception:
#         logger.exception("tool_error expand_context reference=%s", _preview(reference))
#         raise


@tool(description="Look up scripture verses by translation, book, chapter, and verse number in the database. Only returns verses that exist in the DB.")
def scripture_lookup(query: ScriptureQuery) -> str:
    requested_shortname = _norm_shortname(getattr(query, "translation", None))

    logger.info(
        "tool_called scripture_lookup translation=%s book=%s chapter=%s verse=%s",
        _preview(requested_shortname),
        _preview(getattr(query, "book", None)),
        _preview(getattr(query, "chapter", None)),
        _preview(getattr(query, "verse", None)),
    )

    try:
        with Session(engine) as session:
            # Enforce "DB only": if requested translation isn't present, refuse and provide valid options.
            translation = get_translation(requested_shortname, session)
            if not translation:
                translations = list_translations(session)
                shortnames = sorted(
                    {t.translation_shortname for t in translations if getattr(t, "translation_shortname", None)}
                )
                result = (
                    f"Translation '{requested_shortname}' is not available in the database. "
                    f"Available translations: {', '.join(shortnames) if shortnames else '(none)'}. "
                    f"Please choose one of the available translations."
                )
                logger.info(
                    "tool_return scripture_lookup result = %s",
                    _preview(result),
                )
                return result

            book = get_book(query.book, session)
            if not book:
                result = f"Book '{query.book}' not found."
                logger.info(
                    "tool_return scripture_lookup result = %s",
                    _preview(result),
                )
                return result

            if query.verse is not None:
                verse = get_verse(
                    translation,
                    book,
                    query.chapter,
                    query.verse,
                    session
                )
                if not verse:
                    result = "Verse not found."
                    logger.info(
                        "tool_return scripture_lookup result = %s",
                        _preview(result),
                    )
                    return result

                result = (
                    f"{book.book_name} {query.chapter}:{query.verse} ({translation.translation_shortname})\n"
                    f"{verse.text}"
                )
                logger.info(
                    "tool_return scripture_lookup result = %s",
                    _preview(result),
                )
                return result

            verses = get_verses(
                translation,
                book,
                query.chapter,
                session
            )

            if not verses:
                result = "Chapter not found."
                logger.info(
                    "tool_return scripture_lookup result=%s",
                    _preview(result),
                )
                return result

            result = "\n".join(
                f"({translation.translation_shortname}) {book.book_name} {v.chapter_num}:{v.verse_num}. {v.text}"
                for v in verses
            )
            logger.info(
                "tool_return scripture_lookup result_len=%d",
                len(result),
            )
            return result
    except Exception:
        logger.exception("tool_error scripture_lookup query=%s", _preview(query))
        raise


agent_tools = [available_translations, semantic_search, scripture_lookup]
