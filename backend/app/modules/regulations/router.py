import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.core.database import SessionDep
from app.modules.auth.dependencies import CurrentUser
from app.modules.regulations.models import LegalProvision, Regulation, RegulationVersion

router = APIRouter(prefix="/api/v1/regulations", tags=["regulations"])


def visible_to(user_id: uuid.UUID):
    return RegulationVersion.is_internal.is_(False) | RegulationVersion.allowed_user_ids.contains([str(user_id)])


@router.get("")
async def regulations(session: SessionDep, user: CurrentUser):
    rows = (await session.execute(
        select(Regulation, RegulationVersion).join(RegulationVersion).where(
            RegulationVersion.status == "published", visible_to(user.id)
        )
    )).all()
    return [{"id": regulation.id, "number": regulation.regulation_number, "type": regulation.regulation_type,
             "title": regulation.title, "topic": regulation.topic, "version_id": version.id,
             "status": version.status, "source_url": version.source_url} for regulation, version in rows]


@router.get("/{regulation_id}/provisions")
async def provisions(regulation_id: uuid.UUID, session: SessionDep, user: CurrentUser):
    rows = (await session.execute(
        select(LegalProvision).join(RegulationVersion).where(
            RegulationVersion.regulation_id == regulation_id,
            RegulationVersion.status == "published",
            visible_to(user.id),
        )
    )).scalars().all()
    return [{"id": p.id, "article_number": p.article_number, "paragraph_number": p.paragraph_number, "text": p.text}
            for p in rows]
