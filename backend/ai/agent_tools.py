import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from sentence_transformers import SentenceTransformer
from sqlmodel import Session

from .model import model
from ..schemas.scripture import ScriptureQuery
from ..db_session import engine
from ..services.sql_service import (
    get_translation,
    get_book,
    get_verse,
    get_verses,
    list_translations,
    get_semantic_similar_verses,
    get_books,
    get_book_chapters,
    keyword_search_verses # NEW: SELECT ... FROM verses WHERE verse_text ILIKE %query%
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

@tool(description="Get historical and cultural background context for a Bible book. "
                  "Use this when the user asks about the meaning, background, or setting of a passage.")
def get_book_context(book: str) -> str:
    messages = [
        SystemMessage(content="You are a Bible scholar. Return only factual, historically grounded information. No speculation."),
        HumanMessage(content=f"Give a concise scholarly overview of the book of {book}: authorship, date written, original audience, historical setting, and major themes.")
    ]
    response = model.invoke(messages)
    return response.content


@tool(description="Get scholarly commentary and explanation for a specific Bible verse or passage. "
                  "Use this AFTER retrieving the verse text to provide deeper meaning and context.")
def get_verse_commentary(book: str, chapter: int, verse: int, verse_text: str) -> str:
    messages = [
        SystemMessage(content="You are a Bible scholar providing study commentary. Be concise, accurate, and cite relevant cross-references where helpful."),
        HumanMessage(content=f"Provide study commentary for {book} {chapter}:{verse} — \"{verse_text}\". Include: literary context, meaning of key words, theological significance, and 1-2 cross-references.")
    ]
    response = model.invoke(messages)
    return response.content


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
        logger.info("tool_return available_translations result = %s", _preview(result))
        return result
    except Exception:
        logger.exception("TOOL_ERROR!!! available_translations")
        raise


@tool(description="Given RAW text (not a reference or question),"
                  "find semantically similar verses across the Bible. "
                  "Use this AFTER you already have the verse text from scripture_lookup")
def semantic_search(verse_text: str) -> str:
    if re.match(r'^[\w\s]+\d+:\d+$', verse_text.strip()):
        return "Error: you must pass the actual verse text"

    try:
        embedding = embedding_model.encode(verse_text)
        embedding_list = embedding.tolist()
        logger.info(f"semantic_search embedding_list = {verse_text}")
        logger.info(
            f"tool_return semantic_search result = %s\n size of embedding = %s",
            _preview(embedding_list),
            embedding.shape[0]
        )

        with Session(engine) as session:
            result_rows = get_semantic_similar_verses(embedding_list, session)

        formatted = "\n".join(
            f"({row.translation_shortname}) {row.name} {row.chapter_num}:{row.verse_num} - {row.verse_text}"
            for row in result_rows
        )
        result = f"Semantic search results:\n{formatted}"
        logger.info(result)
        return result
    except Exception:
        logger.exception("TOOL_ERROR!!! semantic_search query=%s", _preview(verse_text))
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
                verse = get_verse(translation, book, query.chapter, query.verse, session)
                if not verse:
                    return "Verse not found."
                return verse.verse_text

            # Entire chapter
            verses = get_verses(translation, book, query.chapter, session)
            if not verses:
                return "Chapter not found."

            return "\n".join(
                f"({translation.translation_shortname}) {book.name} {v.chapter_num}:{v.verse_num}. {v.verse_text}"
                for v in verses
            )

    except Exception:
        logger.exception("TOOL_ERROR!!! scripture_lookup")
        raise


@tool(description="List all books of the Bible available in the database. "
                  "Returns book names in canonical order. "
                  "Use this to validate a book name before calling scripture_lookup.")
def list_books() -> str:
    logger.info("tool_called list_books")
    try:
        with Session(engine) as session:
            books = get_books(session)
            names = [b.name for b in books if getattr(b, "book_name", None)]

        result = ", ".join(names) if names else "(none found)"
        logger.info("tool_return list_books result = %s", _preview(result))
        return result
    except Exception:
        logger.exception("TOOL_ERROR!!! list_books")
        raise


@tool(description="Get all chapters available for a given book and translation. "
                  "Returns a list of chapter numbers. "
                  "Useful before calling scripture_lookup to know what chapters exist.")
def list_chapters(book: str, translation: str = "BSB") -> str:
    query_translation = _norm_shortname(translation)
    logger.info("tool_called list_chapters book=%s translation=%s", book, query_translation)

    try:
        with Session(engine) as session:
            trans = get_translation(query_translation, session)
            if not trans:
                return f"Translation '{query_translation}' not found."

            book_obj = get_book(book, session)
            if not book_obj:
                return f"Book '{book}' not found."

            chapters = get_book_chapters(trans, book_obj, session)
            if not chapters:
                return f"No chapters found for {book} in {query_translation}."

        nums = ", ".join(str(c) for c in sorted(chapters))
        result = f"{book} ({query_translation}) has chapters: {nums}"
        logger.info("tool_return list_chapters result = %s", _preview(result))
        return result
    except Exception:
        logger.exception("TOOL_ERROR!!! list_chapters book=%s translation=%s", book, query_translation)
        raise


@tool(description="Search for Bible verses containing a specific word or phrase (case-insensitive keyword match). "
                  "Use this when the user wants to find verses mentioning a topic or word, "
                  "not for semantic/meaning-based search. "
                  "Optionally filter by translation and book.")
def keyword_search(query: str, translation: str = "BSB", book: str = None, limit: int = 10) -> str:
    query_translation = _norm_shortname(translation)
    logger.info(
        "tool_called keyword_search query=%s translation=%s book=%s limit=%s",
        _preview(query), query_translation, book, limit
    )

    try:
        with Session(engine) as session:
            trans = get_translation(query_translation, session)
            if not trans:
                return f"Translation '{query_translation}' not found."

            book_obj = None
            if book:
                book_obj = get_book(book, session)
                if not book_obj:
                    return f"Book '{book}' not found."

            results = keyword_search_verses(query, trans, session, book=book_obj, limit=limit)

        if not results:
            return f"No verses found matching '{query}'."

        formatted = "\n".join(
            f"({row.translation_shortname}) {row.name} {row.chapter_num}:{row.verse_num} - {row.verse_text}"
            for row in results
        )
        result = f"Keyword search results for '{query}':\n{formatted}"
        logger.info("tool_return keyword_search result = %s", _preview(result))
        return result
    except Exception:
        logger.exception("TOOL_ERROR!!! keyword_search query=%s", _preview(query))
        raise


@tool(description="Compare the same verse or chapter across multiple Bible translations side by side. "
                  "Use this when the user wants to see how different translations render the same passage. "
                  "Provide a book, chapter, and optionally a verse number.")
def cross_translation_compare(book: str, chapter: int, verse: int = None) -> str:
    logger.info(
        "tool_called cross_translation_compare book=%s chapter=%s verse=%s",
        book, chapter, verse
    )

    try:
        with Session(engine) as session:
            all_translations = list_translations(session)
            shortnames = sorted(
                {t.translation_shortname for t in all_translations if getattr(t, "translation_shortname", None)}
            )

            book_obj = get_book(book, session)
            if not book_obj:
                return f"Book '{book}' not found."

            sections = []
            for shortname in shortnames:
                trans = get_translation(shortname, session)
                if not trans:
                    continue

                if verse is not None:
                    v = get_verse(trans, book_obj, chapter, verse, session)
                    if v:
                        sections.append(f"[{shortname}] {v.verse_text}")
                else:
                    verses = get_verses(trans, book_obj, chapter, session)
                    if verses:
                        block = "\n".join(
                            f"  {v.verse_num}. {v.verse_text}" for v in verses
                        )
                        sections.append(f"[{shortname}]\n{block}")

        if not sections:
            return "No results found across translations."

        passage = f"{book} {chapter}" + (f":{verse}" if verse else "")
        result = f"Cross-translation comparison for {passage}:\n\n" + "\n\n".join(sections)
        logger.info("tool_return cross_translation_compare result = %s", _preview(result))
        return result
    except Exception:
        logger.exception(
            "TOOL_ERROR!!! cross_translation_compare book=%s chapter=%s verse=%s",
            book, chapter, verse
        )
        raise


agent_tools = [
    available_translations,
    semantic_search,
    scripture_lookup,
    list_books,
    list_chapters,
    keyword_search,
    cross_translation_compare,
    get_book_context,
    get_verse_commentary,
]
