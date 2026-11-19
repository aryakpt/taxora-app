from fastapi import APIRouter, HTTPException

from app.core.database import SessionDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.chat.service import ConversationNotFound, answer_question

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, session: SessionDep, user: CurrentUser):
    try:
        return await answer_question(body, session, user)
    except ConversationNotFound as exc:
        raise HTTPException(404, "Percakapan tidak ditemukan") from exc
