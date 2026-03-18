import re
from typing import Optional
from fastapi import HTTPException
from sqlmodel import Session

from ..schemas.scripture import ScriptureQuery, DEFAULT_TRANSLATION
from ..services.sql_service import get_book, get_translation, get_verse, get_verses

COMMENTARY_KEYWORDS = [
    "explain",
    "meaning",
    "what does",
    "why does",
    "interpret",
    "commentary",
    "compare",
    "background",
    "context",
    "sermon",
]


def wants_commentary(text: str) -> bool:
    lower = text.lower()
    for keyword in COMMENTARY_KEYWORDS:
        if keyword in lower:
            return True
    return False


def try_parse_scripture_query(text: str) -> Optional[ScriptureQuery]:
    """
    Attempts to parse a simple scripture reference like:
    - John 3
    - John 3:16
    - John 3:16 ESV
    - 1 John 2:3
    """
    pattern = r"""
        ^\s*
        (?P<book>[1-3]?\s?[A-Za-z]+)
        \s+
        (?P<chapter>\d+)
        (?:
            :
            (?P<verse>\d+)
        )?
        (?:\s+(?P<translation>[A-Za-z]+))?
        \s*$
    """
    match = re.match(pattern, text.strip(), re.VERBOSE | re.IGNORECASE)
    if not match:
        return None

    groups = match.groupdict()

    return ScriptureQuery(
        book=groups["book"].strip(),
        chapter=int(groups["chapter"]),
        verse=int(groups["verse"]) if groups["verse"] else None,
        translation=(groups["translation"] or DEFAULT_TRANSLATION).upper(),
    )


def scripture_lookup_from_db(parsed: ScriptureQuery, session: Session) -> str:
    translation = get_translation(parsed.translation, session=session)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    book = get_book(parsed.book, session=session)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    chapter = parsed.chapter
    verse = parsed.verse

    if verse is not None:
        v = get_verse(translation, book, chapter, verse, session=session)
        if not v:
            raise HTTPException(status_code=404, detail="Verse not found")
        return f"{book.book_name} {chapter}:{verse} ({translation.translation_shortname})\n{v.verse_text}"

    verses = get_verses(translation, book, chapter, session=session)
    if not verses:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return "\n".join(
        f"{book.book_name} {vv.chapter_num}:{vv.verse_num} ({translation.translation_shortname}) {vv.verse_text}"
        for vv in verses
    )
