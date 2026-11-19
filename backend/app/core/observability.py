import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("taxora")
REQUEST_ID_HEADER = "X-Request-ID"


def configure_logging() -> None:
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def install(app: FastAPI) -> None:
    """Attach a request ID to every request, log method/path/status/latency, and hide internal errors.

    Request bodies are never logged: questions may contain sensitive tax data (PRD §9, §10.4).
    """

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled error request_id=%s path=%s", request_id, request.url.path)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )
        latency_ms = round((time.monotonic() - started) * 1000)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%s",
            request_id, request.method, request.url.path, response.status_code, latency_ms,
        )
        return response
