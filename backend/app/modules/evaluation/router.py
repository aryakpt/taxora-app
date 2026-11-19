from fastapi import APIRouter

from app.modules.auth.dependencies import AdminUser

router = APIRouter(prefix="/api/v1/admin/evaluations", tags=["admin"])


@router.get("")
async def evaluations(user: AdminUser):
    return {"available": False, "detail": "Dataset evaluasi hukum terverifikasi belum disediakan; tidak ada skor yang diklaim."}
