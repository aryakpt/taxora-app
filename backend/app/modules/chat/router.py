from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.database import SessionDep
from app.core.rate_limit import enforce
from app.modules.auth.dependencies import CurrentUser
from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.chat.service import ConversationNotFound, answer_question

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, session: SessionDep, user: CurrentUser):
    # Per account, so one user cannot exhaust the shared LLM quota.
    enforce(f"chat:{user.id}", settings.chat_requests_per_hour, window_seconds=3600)
    try:
        return await answer_question(body, session, user)
    except ConversationNotFound as exc:
        raise HTTPException(404, "Percakapan tidak ditemukan") from exc
