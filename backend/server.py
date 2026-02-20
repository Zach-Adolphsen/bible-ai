from contextlib import asynccontextmanager
from typing import Annotated, Optional
import logging
import re

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Session

from backend.ai.agent import send_prompt
from backend.ai.schema import ScriptureQuery, DEFAULT_TRANSLATION
from backend.db_session import get_session
from backend.services.sql_model import Translation
from backend.services.sql_service import get_book, get_translation, get_verse, get_verses

logger = logging.getLogger(__name__)

SessionDep = Annotated[Session, Depends(get_session)]

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


def _wants_commentary(text: str) -> bool:
    lower = text.lower()

    for keyword in COMMENTARY_KEYWORDS:
        if keyword in lower:
            return True

    return False


def _try_parse_scripture_query(text: str) -> Optional[ScriptureQuery]:
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

def _scripture_lookup_from_db(parsed: ScriptureQuery, session: Session) -> str:
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("Starting backend")
    yield
    logger.info("Shutting down backend")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    answer: str


@app.get("/")
async def root():
    return {"Health": "OK"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, session: SessionDep) -> ChatResponse:

    parsed = _try_parse_scripture_query(req.prompt)

    # If it's a clean scripture reference AND no commentary requested,
    # bypass the agent entirely
    if parsed is not None and not _wants_commentary(req.prompt):
        answer = _scripture_lookup_from_db(parsed, session=session)
        return ChatResponse(answer=answer)

    # Otherwise use the agent (commentary, compare, etc.)
    try:
        answer = send_prompt(req.prompt)
        return ChatResponse(answer=answer)
    except Exception as e:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail="Agent error") from e



@app.get("/bible/{translation}")
async def api_get_translation(translation: str, session: SessionDep) -> Translation:
    translation = get_translation(translation, session=session)

    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    return translation


@app.get("/bible/{translation}/{book}")
async def get_translation_book(translation: str, book: str, session: SessionDep):
    translation = get_translation(translation, session=session)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    book = get_book(book, session=session)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return {"translation": translation, "book": book}


@app.get("/bible/{translation}/{book}/{chapter:int}")
async def get_translation_book_chapter(translation: str, book: str, chapter: int, session: SessionDep):
    translation = get_translation(translation, session=session)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    book = get_book(book, session=session)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book_verses = get_verses(translation, book, chapter, session=session)
    if not book_verses:
        raise HTTPException(status_code=404, detail="Chapter not found")

    merged_dict = {
        "translation": translation,
        "book": book,
        "chapter": {}
    }

    for verse in book_verses:
        chapter_num: int = verse.chapter_num
        if chapter_num not in merged_dict["chapter"]:
            merged_dict["chapter"][chapter_num] = []
        merged_dict["chapter"][chapter_num].append({
            "verse_number": verse.verse_num,
            "verse_text": verse.verse_text
        })

    return merged_dict


@app.get("/bible/{translation}/{book}/{chapter:int}/{verse:int}")
async def get_translation_verse(translation: str, book: str, chapter: int, verse: int, session: SessionDep):
    translation = get_translation(translation, session=session)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    book = get_book(book, session=session)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book_verse = get_verse(translation, book, chapter, verse, session=session)
    if not book_verse:
        raise HTTPException(status_code=404, detail="Verse not found")

    merged_dict = {
        "translation": translation,
        "book": book,
        "chapter": {}
    }

    chapter_num: int = book_verse.chapter_num
    if chapter_num not in merged_dict["chapter"]:
        merged_dict["chapter"][chapter_num] = []
    merged_dict["chapter"][chapter_num].append({
        "verse_number": book_verse.verse_num,
        "verse_text": book_verse.verse_text
    })

    return merged_dict
