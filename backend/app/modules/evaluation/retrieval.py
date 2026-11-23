"""Offline evaluation of the scope guard and retrieval (PRD §11). No LLM is called, so it is free and
repeatable; answer quality needs a separate, reviewed evaluation.

Each case expects one of:
    answer       in scope, and an expected article of the expected regulation is in the top k results
    out_of_scope refused by the scope guard
    not_in_kb    in scope, but the knowledge base has no source yet. Retrieval returning chunks here is not a
                 failure by itself (the LLM must still refuse), so these are reported, not scored.
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.evaluation.models import EvaluationRun
from app.modules.generation.embeddings import Embedder
from app.modules.query_understanding.period import reference_date
from app.modules.query_understanding.scope import assess_scope
from app.modules.retrieval.service import hybrid_search

CASES_DIR = Path(__file__).parent / "cases"
NOBODY = uuid.UUID(int=0)  # no user: only non-internal documents are searched


class Case(BaseModel):
    id: str
    question: str
    expect: Literal["answer", "out_of_scope", "not_in_kb"]
    regulation: str | None = None
    articles: list[str] = []


class Dataset(BaseModel):
    name: str
    description: str
    reviewed_by: str | None
    cases: list[Case]


@dataclass
class CaseResult:
    id: str
    expect: str
    passed: bool | None  # None: reported, not scored
    in_scope: bool
    rank: int | None = None  # 1-based position of the first expected article, if found
    retrieved: list[str] = field(default_factory=list)


def load(name: str = "pmk_28_2026") -> Dataset:
    return Dataset.model_validate(json.loads((CASES_DIR / f"{name}.json").read_text()))


def _label(item: dict) -> str:
    return f"{item['regulation_number']} Pasal {item['article_number']}" if item["article_number"] else \
        f"{item['regulation_number']} (bagian lain)"


async def evaluate_case(session: AsyncSession, case: Case, embedder: Embedder,
                        statuses: tuple[str, ...]) -> CaseResult:
    scope = await assess_scope(case.question, embedder)
    if case.expect == "out_of_scope":
        return CaseResult(case.id, case.expect, passed=not scope.in_scope, in_scope=scope.in_scope)
    if not scope.in_scope:
        return CaseResult(case.id, case.expect, passed=False if case.expect == "answer" else None, in_scope=False)

    evidence = await hybrid_search(session, case.question, NOBODY, reference_date(case.question), embedder,
                                   statuses=statuses)
    retrieved = [_label(item) for item in evidence]
    if case.expect == "not_in_kb":
        return CaseResult(case.id, case.expect, passed=None, in_scope=True, retrieved=retrieved)
    rank = next((position for position, item in enumerate(evidence, 1)
                 if item["regulation_number"] == case.regulation and item["article_number"] in case.articles), None)
    return CaseResult(case.id, case.expect, passed=rank is not None, in_scope=True, rank=rank, retrieved=retrieved)


async def run(session: AsyncSession, dataset: Dataset, embedder: Embedder, *,
              include_unreviewed: bool = False) -> dict:
    statuses = ("published", "review_required", "approved") if include_unreviewed else ("published",)
    results = [await evaluate_case(session, case, embedder, statuses) for case in dataset.cases]
    answer = [r for r in results if r.expect == "answer"]
    refused = [r for r in results if r.expect == "out_of_scope"]
    found = [r.rank for r in answer if r.rank]
    summary = {
        "dataset": dataset.name,
        "dataset_reviewed_by": dataset.reviewed_by,
        "statuses": list(statuses),
        "top_k": settings.retrieval_top_k,
        "settings": {"retrieval_max_cosine_distance": settings.retrieval_max_cosine_distance,
                     "retrieval_keyword_weight": settings.retrieval_keyword_weight,
                     "scope_min_similarity": settings.scope_min_similarity,
                     "embedding_model": settings.embedding_model},
        "hit_rate": _ratio(len(found), len(answer)),
        "mean_reciprocal_rank": round(sum(1 / rank for rank in found) / len(answer), 3) if answer else None,
        "out_of_scope_refused": _ratio(sum(r.passed for r in refused), len(refused)),
        "not_in_kb_with_results": sum(1 for r in results if r.expect == "not_in_kb" and r.retrieved),
        "cases": [asdict(r) for r in results],
    }
    session.add(EvaluationRun(name=dataset.name, results=summary))
    return summary


def _ratio(numerator: int, denominator: int) -> dict:
    return {"passed": numerator, "total": denominator,
            "rate": round(numerator / denominator, 3) if denominator else None}
