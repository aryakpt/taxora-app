"""Offline retrieval evaluation, run against a labeled fixture regulation (not real law)."""

import pytest

from app.core.database import SessionLocal
from app.modules.auth.models import UserRole
from app.modules.evaluation import retrieval
from app.modules.evaluation.retrieval import Case, Dataset
from tests.fakes import FakeEmbedder
from tests.test_chat import seed_fixture_regulation
from tests.test_ingestion import sign_in_as

DATASET = Dataset(name="fixture", description="fixture", reviewed_by=None, cases=[
    Case(id="rent", question="Berapa tarif pajak atas sewa?", expect="answer",
         regulation="FIXTURE-1/2026", articles=["1"]),
    Case(id="wrong-article", question="Berapa tarif pajak atas sewa?", expect="answer",
         regulation="FIXTURE-1/2026", articles=["9"]),
    Case(id="recipe", question="Bagaimana resep rendang?", expect="out_of_scope"),
    Case(id="gap", question="Berapa tarif PPN?", expect="not_in_kb"),
])


def test_the_shipped_dataset_is_valid():
    dataset = retrieval.load()

    assert len({case.id for case in dataset.cases}) == len(dataset.cases)
    assert all(case.articles and case.regulation for case in dataset.cases if case.expect == "answer")
    assert {case.expect for case in dataset.cases} == {"answer", "out_of_scope", "not_in_kb"}


@pytest.mark.db
async def test_scores_are_computed_and_stored(client):
    await seed_fixture_regulation()

    async with SessionLocal() as session, session.begin():
        summary = await retrieval.run(session, DATASET, FakeEmbedder())

    results = {case["id"]: case for case in summary["cases"]}
    assert results["rent"]["passed"] and results["rent"]["rank"] == 1
    assert results["wrong-article"]["passed"] is False
    assert results["recipe"]["passed"] and not results["recipe"]["in_scope"]
    assert results["gap"]["passed"] is None and summary["not_in_kb_with_results"] == 1
    assert summary["hit_rate"] == {"passed": 1, "total": 2, "rate": 0.5}
    assert summary["out_of_scope_refused"]["rate"] == 1.0

    await sign_in_as(client, "admin@example.com", UserRole.admin)
    runs = (await client.get("/api/v1/admin/evaluations")).json()
    assert runs[0]["name"] == "fixture" and runs[0]["results"]["hit_rate"]["passed"] == 1


@pytest.mark.db
async def test_unreviewed_documents_are_only_searched_on_request():
    await seed_fixture_regulation(status="review_required")

    async with SessionLocal() as session, session.begin():
        published_only = await retrieval.run(session, DATASET, FakeEmbedder())
        draft = await retrieval.run(session, DATASET, FakeEmbedder(), include_unreviewed=True)

    assert published_only["hit_rate"]["passed"] == 0
    assert draft["hit_rate"]["passed"] == 1
