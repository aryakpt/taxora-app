from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core import observability
from app.core.config import settings
from app.core.database import SessionDep
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.conversations.router import router as conversations_router
from app.modules.evaluation.router import router as evaluation_router
from app.modules.feedback.router import router as feedback_router
from app.modules.ingestion.router import router as ingestion_router
from app.modules.regulations.router import router as regulations_router


def create_app() -> FastAPI:
    observability.configure_logging()
    app = FastAPI(title="Taxora API", version="0.1.0")

    # Registered before CORS so CORS stays outermost and also decorates error responses.
    observability.install(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", observability.REQUEST_ID_HEADER],
        expose_headers=[observability.REQUEST_ID_HEADER],
    )

    for router in (
        auth_router,
        chat_router,
        conversations_router,
        regulations_router,
        feedback_router,
        ingestion_router,
        evaluation_router,
    ):
        app.include_router(router)

    @app.get("/api/v1/health", tags=["health"])
    async def health(session: SessionDep):
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            observability.logger.exception("health check: database unavailable")
            return JSONResponse(status_code=503, content={"status": "degraded", "database": "unavailable"})
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
