"""Renaming and deleting conversations."""

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.auth.models import UserRole
from app.modules.conversations.models import Conversation, Message
from app.modules.feedback.models import Feedback
from tests.test_ingestion import sign_in_as

pytestmark = pytest.mark.db


async def new_conversation(client, question: str) -> str:
    response = await client.post("/api/v1/chat", json={"question": question})
    assert response.status_code == 200, response.text
    return response.json()["conversation_id"]


async def titles(client) -> list[str]:
    return [row["title"] for row in (await client.get("/api/v1/conversations")).json()]


async def test_rename_changes_the_title_but_not_the_order(client):
    await sign_in_as(client, "owner@example.com", UserRole.user)
    first = await new_conversation(client, "Berapa tarif pajak atas sewa?")
    await new_conversation(client, "Apakah faktur pajak wajib?")
    before = await titles(client)

    response = await client.patch(f"/api/v1/conversations/{first}", json={"title": "  Sewa gudang  "})

    assert response.status_code == 200 and response.json()["title"] == "Sewa gudang"
    assert await titles(client) == [before[0], "Sewa gudang"]  # still second: renaming is not activity


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
async def test_invalid_titles_are_rejected(client, title):
    await sign_in_as(client, "owner@example.com", UserRole.user)
    conversation = await new_conversation(client, "Berapa tarif pajak atas sewa?")

    assert (await client.patch(f"/api/v1/conversations/{conversation}", json={"title": title})).status_code == 422


async def test_delete_removes_messages_and_feedback(client):
    await sign_in_as(client, "owner@example.com", UserRole.user)
    conversation = await new_conversation(client, "Berapa tarif pajak atas sewa?")
    detail = (await client.get(f"/api/v1/conversations/{conversation}")).json()
    answer = next(m for m in detail["messages"] if m["role"] == "assistant")
    await client.post("/api/v1/feedback", json={"message_id": answer["id"], "rating": "negative"})

    assert (await client.delete(f"/api/v1/conversations/{conversation}")).status_code == 200

    assert (await client.get(f"/api/v1/conversations/{conversation}")).status_code == 404
    async with SessionLocal() as session:
        for model in (Conversation, Message, Feedback):
            assert await session.scalar(select(func.count()).select_from(model)) == 0


async def test_other_users_conversations_cannot_be_renamed_or_deleted(client):
    await sign_in_as(client, "owner@example.com", UserRole.user)
    conversation = await new_conversation(client, "Berapa tarif pajak atas sewa?")

    await sign_in_as(client, "stranger@example.com", UserRole.user)
    assert (await client.patch(f"/api/v1/conversations/{conversation}", json={"title": "milik saya"})).status_code == 404
    assert (await client.delete(f"/api/v1/conversations/{conversation}")).status_code == 404

    await sign_in_as(client, "owner@example.com", UserRole.user)
    assert await titles(client) == ["Berapa tarif pajak atas sewa?"]
