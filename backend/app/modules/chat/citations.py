"""Validate the LLM's structured output against the evidence that was actually retrieved.

Checking JSON structure is not enough (PRD §8.5): a claim is kept only if it cites evidence that
was given to the model AND its quote appears verbatim (ignoring case and whitespace) in that evidence.
"""

import json
import re
import uuid
from dataclasses import dataclass, field

MIN_QUOTE_CHARS = 20
MAX_LIST_ITEMS = 10
MAX_ITEM_CHARS = 500


class MalformedOutput(Exception):
    """The model did not return the expected JSON object."""


@dataclass
class ValidatedClaim:
    text: str
    evidence_ids: list[uuid.UUID]
    quote: str  # verbatim excerpt from the source text, not the model's copy


@dataclass
class GenerationResult:
    in_scope: bool
    answer: str
    claims: list[ValidatedClaim] = field(default_factory=list)
    rejected_claims: int = 0
    missing_information: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def find_verbatim(quote: str, source_text: str) -> str | None:
    """Return the exact source passage matching `quote`, tolerating case and whitespace differences."""
    words = quote.split()
    if len(" ".join(words)) < MIN_QUOTE_CHARS:
        return None
    match = re.search(r"\s+".join(map(re.escape, words)), source_text, flags=re.IGNORECASE)
    return match.group(0) if match else None


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [item.strip()[:MAX_ITEM_CHARS] for item in value if isinstance(item, str) and item.strip()]
    return items[:MAX_LIST_ITEMS]


def _validate_claim(raw, evidence_text: dict[str, str]) -> ValidatedClaim | None:
    if not isinstance(raw, dict):
        return None
    text, quote, ids = raw.get("text"), raw.get("quote"), raw.get("evidence_ids")
    if not isinstance(text, str) or not text.strip() or not isinstance(quote, str) or not isinstance(ids, list):
        return None
    supporting, verbatim = [], None
    for evidence_id in ids:
        source = evidence_text.get(str(evidence_id))
        found = find_verbatim(quote, source) if source else None
        if found:
            supporting.append(uuid.UUID(str(evidence_id)))
            verbatim = verbatim or found
    if not supporting:
        return None
    return ValidatedClaim(text=text.strip(), evidence_ids=supporting, quote=verbatim)


def parse_and_validate(raw_output: str, evidence: list[dict]) -> GenerationResult:
    try:
        payload = json.loads(raw_output)
    except (ValueError, TypeError) as exc:
        raise MalformedOutput("not JSON") from exc
    if not isinstance(payload, dict):
        raise MalformedOutput("not a JSON object")

    if payload.get("in_scope") is False:
        return GenerationResult(in_scope=False, answer="")

    evidence_text = {str(item["id"]): item["text"] for item in evidence}
    raw_claims = payload.get("claims") if isinstance(payload.get("claims"), list) else []
    claims = [claim for raw in raw_claims if (claim := _validate_claim(raw, evidence_text))]
    answer = payload.get("answer") if isinstance(payload.get("answer"), str) else ""
    return GenerationResult(
        in_scope=True,
        answer=answer.strip(),
        claims=claims,
        rejected_claims=len(raw_claims) - len(claims),
        missing_information=_string_list(payload.get("missing_information")),
        limitations=_string_list(payload.get("limitations")),
    )
