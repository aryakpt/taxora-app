import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints

from app.core.database import SessionDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.conversations.models import Conversation, Message
from app.modules.feedback.models import Feedback

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: Literal["positive", "negative"]
    # Matches user_feedback.reason (String(100)).
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None


@router.post("")
async def feedback(body: FeedbackRequest, session: SessionDep, user: CurrentUser):
    message = await session.get(Message, body.message_id)
    conversation = await session.get(Conversation, message.conversation_id) if message else None
    if message is None or conversation is None or conversation.user_id != user.id or message.role != "assistant":
        raise HTTPException(404, "Jawaban tidak ditemukan")
    session.add(Feedback(user_id=user.id, message_id=message.id, rating=body.rating, reason=body.reason or None))
    return {"saved": True}
