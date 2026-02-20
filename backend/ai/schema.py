from pydantic import BaseModel
from typing import Optional


class ScriptureQuery(BaseModel):
    translation: str = "BSB"
    book: str
    chapter: int
    verse: Optional[int] = None
