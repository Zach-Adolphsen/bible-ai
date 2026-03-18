import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ...db_session import get_session
from ...ai.agent import send_prompt
from ...schemas.chat import ChatRequest, ChatResponse
from ...services.scripture_service import try_parse_scripture_query, wants_commentary, scripture_lookup_from_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, session: SessionDep) -> ChatResponse:
    parsed = try_parse_scripture_query(req.prompt)

    # If it's a clean scripture reference AND no commentary requested,
    # bypass the agent entirely
    if parsed is not None and not wants_commentary(req.prompt):
        answer = scripture_lookup_from_db(parsed, session=session)
        return ChatResponse(answer=answer)

    # Otherwise use the agent (commentary, compare, etc.)
    try:
        answer = send_prompt(req.prompt)
        return ChatResponse(answer=answer)
    except Exception as e:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail="Agent error") from e
