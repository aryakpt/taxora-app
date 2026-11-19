import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.database import SessionDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.conversations.models import Conversation, Message

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("")
async def conversations(session: SessionDep, user: CurrentUser):
    rows = (await session.scalars(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())
    )).all()
    return [{"id": row.id, "title": row.title, "updated_at": row.updated_at} for row in rows]


@router.get("/{conversation_id}")
async def conversation_detail(conversation_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    row = await session.get(Conversation, conversation_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    messages = (await session.scalars(
        select(Message).where(Message.conversation_id == row.id).order_by(Message.created_at)
    )).all()
    return {
        "id": row.id,
        "title": row.title,
        "messages": [{"id": m.id, "role": m.role, "content": m.content, "metadata": m.metadata_json} for m in messages],
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    row = await session.get(Conversation, conversation_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    await session.delete(row)
    return {"deleted": True}
