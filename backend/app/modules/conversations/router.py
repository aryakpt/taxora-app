import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select, update

from app.core.database import SessionDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.conversations.models import Conversation, Message

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class RenameRequest(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


async def _own(session, conversation_id: uuid.UUID, user) -> Conversation:
    """The user's own conversation; another user's is reported as not found, not as forbidden."""
    row = await session.get(Conversation, conversation_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    return row


@router.get("")
async def conversations(session: SessionDep, user: CurrentUser):
    rows = (await session.scalars(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())
    )).all()
    return [{"id": row.id, "title": row.title, "updated_at": row.updated_at} for row in rows]


@router.get("/{conversation_id}")
async def conversation_detail(conversation_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    row = await _own(session, conversation_id, user)
    messages = (await session.scalars(
        select(Message).where(Message.conversation_id == row.id).order_by(*Message.chronological())
    )).all()
    return {"id": row.id, "title": row.title, "messages": [_shown(message) for message in messages]}


def _shown(message: Message) -> dict:
    """What the conversation view needs. The rest of the stored trace (model, errors, prompt version, evidence
    ids) stays on the server. Answers from before sources were stored have no sources to show."""
    meta = message.metadata_json or {}
    shown = {"id": message.id, "role": message.role, "content": message.content}
    if message.role == "assistant":
        display = meta.get("display") or {}
        shown |= {
            "answer_status": meta.get("answer_status"),
            "sources": display.get("sources", []),
            "missing_information": display.get("missing_information", []),
            "limitations": display.get("limitations", []),
            "latency_ms": meta.get("latency_ms"),
        }
    return shown


@router.patch("/{conversation_id}")
async def rename_conversation(conversation_id: uuid.UUID, body: RenameRequest, session: SessionDep, user: CurrentUser):
    await _own(session, conversation_id, user)
    # Keep updated_at (the ORM would bump it): renaming is not new activity, so the list order stays.
    renamed = (await session.execute(
        update(Conversation).where(Conversation.id == conversation_id)
        .values(title=body.title, updated_at=Conversation.updated_at)
        .returning(Conversation.id, Conversation.title, Conversation.updated_at)
        .execution_options(synchronize_session=False)
    )).one()
    return {"id": renamed.id, "title": renamed.title, "updated_at": renamed.updated_at}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    """Deletes the conversation with its messages and their feedback (database cascade)."""
    row = await _own(session, conversation_id, user)
    await session.delete(row)
    return {"deleted": True}
