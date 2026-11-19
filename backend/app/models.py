"""Import every module's models so Base.metadata is complete (Alembic, tests)."""

from app.core.database import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.conversations.models import Conversation, Message
from app.modules.evaluation.models import EvaluationRun
from app.modules.feedback.models import Feedback
from app.modules.ingestion.models import IngestionJob
from app.modules.regulations.models import DocumentChunk, LegalProvision, Regulation, RegulationVersion

__all__ = [
    "AuditLog",
    "Base",
    "Conversation",
    "DocumentChunk",
    "EvaluationRun",
    "Feedback",
    "IngestionJob",
    "LegalProvision",
    "Message",
    "Regulation",
    "RegulationVersion",
    "User",
]
