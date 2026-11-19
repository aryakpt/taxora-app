import uuid

from fastapi import APIRouter, HTTPException

from app.core.database import SessionDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.conversations.models import Conversation, Message
from app.modules.feedback.models import Feedback

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("")
async def feedback(body: dict, session: SessionDep, user: CurrentUser):
    try:
        message_id = uuid.UUID(str(body["message_id"]))
        rating = body["rating"]
        if rating not in ("positive", "negative"):
            raise ValueError
    except (KeyError, ValueError) as exc:
        raise HTTPException(422, "Feedback tidak valid") from exc
    message = await session.get(Message, message_id)
    conversation = await session.get(Conversation, message.conversation_id) if message else None
    if message is None or conversation is None or conversation.user_id != user.id or message.role != "assistant":
        raise HTTPException(404, "Jawaban tidak ditemukan")
    session.add(Feedback(user_id=user.id, message_id=message_id, rating=rating, reason=body.get("reason")))
    return {"saved": True}
