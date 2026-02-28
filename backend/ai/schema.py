from pydantic import BaseModel, Field
from typing import Optional

DEFAULT_TRANSLATION = "BSB"

class ScriptureQuery(BaseModel):
    book: str
    chapter: int
    verse: Optional[int] = None
    translation: str = Field(default=DEFAULT_TRANSLATION)
