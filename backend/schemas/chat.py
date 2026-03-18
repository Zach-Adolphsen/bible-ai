from typing import Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    id: Optional[str] = None
    role: str = "user"
    prompt: str = Field(min_length=1, max_length=8000)

class ChatResponse(BaseModel):
    id: Optional[str] = None
    role: str = "assistant"
    answer: str
