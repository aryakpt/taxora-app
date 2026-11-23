import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.conversations.models import Conversation, ConversationGroup, Message

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
groups_router = APIRouter(prefix="/api/v1/conversation-groups", tags=["conversations"])

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
GroupName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ConversationUpdate(BaseModel):
    """Either field may be sent alone. `group_id: null` takes the conversation out of its group."""
    title: Title | None = None
    group_id: uuid.UUID | None = None


class GroupRequest(BaseModel):
    name: GroupName


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
    return [_summary(row) for row in rows]


def _summary(row) -> dict:
    return {"id": row.id, "title": row.title, "group_id": row.group_id, "updated_at": row.updated_at}


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
async def update_conversation(conversation_id: uuid.UUID, body: ConversationUpdate, session: SessionDep,
                              user: CurrentUser):
    """Rename and/or move to a group."""
    await _own(session, conversation_id, user)
    changes = {}
    if "title" in body.model_fields_set:
        if body.title is None:
            raise HTTPException(422, "Judul tidak boleh kosong")
        changes["title"] = body.title
    if "group_id" in body.model_fields_set:
        if body.group_id is not None:
            await _own_group(session, body.group_id, user)
        changes["group_id"] = body.group_id
    if not changes:
        raise HTTPException(422, "Tidak ada perubahan")
    # Keep updated_at (the ORM would bump it): renaming or moving is not new activity, so the list order stays.
    updated = (await session.execute(
        update(Conversation).where(Conversation.id == conversation_id)
        .values(**changes, updated_at=Conversation.updated_at)
        .returning(Conversation.id, Conversation.title, Conversation.group_id, Conversation.updated_at)
        .execution_options(synchronize_session=False)
    )).one()
    return _summary(updated)


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    """Deletes the conversation with its messages and their feedback (database cascade)."""
    row = await _own(session, conversation_id, user)
    await session.delete(row)
    return {"deleted": True}


async def _own_group(session, group_id: uuid.UUID, user) -> ConversationGroup:
    row = await session.get(ConversationGroup, group_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Grup tidak ditemukan")
    return row


def _group(row: ConversationGroup) -> dict:
    return {"id": row.id, "name": row.name, "created_at": row.created_at}


async def _save_group(session, row: ConversationGroup) -> dict:
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as exc:
        raise HTTPException(409, "Nama grup sudah dipakai") from exc
    await session.refresh(row)
    return _group(row)


@groups_router.get("")
async def groups(session: SessionDep, user: CurrentUser):
    rows = (await session.scalars(
        select(ConversationGroup).where(ConversationGroup.user_id == user.id)
        .order_by(func.lower(ConversationGroup.name))
    )).all()
    return [_group(row) for row in rows]


@groups_router.post("", status_code=201)
async def create_group(body: GroupRequest, session: SessionDep, user: CurrentUser):
    row = ConversationGroup(user_id=user.id, name=body.name)
    session.add(row)
    return await _save_group(session, row)


@groups_router.patch("/{group_id}")
async def rename_group(group_id: uuid.UUID, body: GroupRequest, session: SessionDep, user: CurrentUser):
    row = await _own_group(session, group_id, user)
    row.name = body.name
    return await _save_group(session, row)


@groups_router.delete("/{group_id}")
async def delete_group(group_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    """Deletes only the group; its conversations stay, ungrouped (the foreign key sets them to NULL)."""
    row = await _own_group(session, group_id, user)
    await session.delete(row)
    return {"deleted": True}
