from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ...db_session import get_session
from ...schemas.models import Translation
from ...services.sql_service import get_book, get_translation, get_verse, get_verses

router = APIRouter(prefix="/bible", tags=["bible"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/{translation}")
async def api_get_translation(translation: str, session: SessionDep) -> Translation:
    translation_obj = get_translation(translation, session=session)

    if not translation_obj:
        raise HTTPException(status_code=404, detail="Translation not found")

    return translation_obj


@router.get("/{translation}/{book}")
async def get_translation_book(translation: str, book: str, session: SessionDep):
    translation_obj = get_translation(translation, session=session)
    if not translation_obj:
        raise HTTPException(status_code=404, detail="Translation not found")

    book_obj = get_book(book, session=session)
    if not book_obj:
        raise HTTPException(status_code=404, detail="Book not found")

    return {"translation": translation_obj, "book": book_obj}


@router.get("/{translation}/{book}/{chapter:int}")
async def get_translation_book_chapter(translation: str, book: str, chapter: int, session: SessionDep):
    translation_obj = get_translation(translation, session=session)
    if not translation_obj:
        raise HTTPException(status_code=404, detail="Translation not found")

    book_obj = get_book(book, session=session)
    if not book_obj:
        raise HTTPException(status_code=404, detail="Book not found")

    book_verses = get_verses(translation_obj, book_obj, chapter, session=session)
    if not book_verses:
        raise HTTPException(status_code=404, detail="Chapter not found")

    merged_dict = {
        "translation": translation_obj,
        "book": book_obj,
        "chapter": {}
    }

    for verse in book_verses:
        chapter_num: int | None = verse.chapter_num
        if chapter_num not in merged_dict["chapter"]:
            merged_dict["chapter"][chapter_num] = []
        merged_dict["chapter"][chapter_num].append({
            "verse_number": verse.verse_num,
            "verse_text": verse.verse_text
        })

    return merged_dict


@router.get("/{translation}/{book}/{chapter:int}/{verse:int}")
async def get_translation_verse(translation: str, book: str, chapter: int, verse: int, session: SessionDep):
    translation_obj = get_translation(translation, session=session)
    if not translation_obj:
        raise HTTPException(status_code=404, detail="Translation not found")

    book_obj = get_book(book, session=session)
    if not book_obj:
        raise HTTPException(status_code=404, detail="Book not found")

    book_verse = get_verse(translation_obj, book_obj, chapter, verse, session=session)
    if not book_verse:
        raise HTTPException(status_code=404, detail="Verse not found")

    merged_dict = {
        "translation": translation_obj,
        "book": book_obj,
        "chapter": {}
    }

    chapter_num: int | None = book_verse.chapter_num
    if chapter_num not in merged_dict["chapter"]:
        merged_dict["chapter"][chapter_num] = []
    merged_dict["chapter"][chapter_num].append({
        "verse_number": book_verse.verse_num,
        "verse_text": book_verse.verse_text
    })

    return merged_dict
