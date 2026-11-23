from fastapi import APIRouter
from sqlalchemy import select

from app.core.database import SessionDep
from app.modules.auth.dependencies import AdminUser
from app.modules.evaluation.models import EvaluationRun

router = APIRouter(prefix="/api/v1/admin/evaluations", tags=["admin"])


@router.get("")
async def evaluations(session: SessionDep, user: AdminUser):
    """Recent offline evaluation runs (`make eval`). Scores are only as good as the dataset: check
    `dataset_reviewed_by` before relying on them."""
    runs = (await session.scalars(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(20))).all()
    return [{"id": run.id, "name": run.name, "created_at": run.created_at, "results": run.results} for run in runs]
