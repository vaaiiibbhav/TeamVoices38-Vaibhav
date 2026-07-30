"""The weighted confidence composite. Computed, never self-reported.

retrieval 0.40, answer support 0.30, slot completeness 0.15,
source authority 0.10, freshness 0.05. Token-overlap stands in for real
entailment for now, per build_spec (upgrade to an NLI model only if time
allows).
"""
from __future__ import annotations

import re

from services.api.graph.slots import REQUIRED_SLOTS
from services.api.rag.schemas import Source

RETRIEVAL_WEIGHT = 0.40
ENTAILMENT_WEIGHT = 0.30
SLOT_WEIGHT = 0.15
AUTHORITY_WEIGHT = 0.10
FRESHNESS_WEIGHT = 0.05

NO_POLICY_MATCH_THRESHOLD = 0.35
ENTAILMENT_THRESHOLD = 0.30
CONFLICT_SCORE_DELTA = 0.05
STALE_THRESHOLD = 0.50

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _retrieval_score(sources: list[Source]) -> float:
    if not sources:
        return 0.0
    return max(0.0, min(1.0, sources[0].score))


def _entailment_score(answer: str | None, sources: list[Source]) -> float:
    if not answer or not sources:
        return 0.0
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0
    source_tokens = _tokenize(" ".join(s.snippet for s in sources))
    return len(answer_tokens & source_tokens) / len(answer_tokens)


def _slot_score(intent: str, missing: list[str]) -> float:
    required = REQUIRED_SLOTS.get(intent, [])
    if not required:
        return 1.0
    return max(0.0, (len(required) - len(missing)) / len(required))


def _authority_score(sources: list[Source]) -> float:
    # No per-document trust tiers yet (Phase 6 supersession tracking). Any
    # retrieved chunk comes from an ingested official policy PDF, so it
    # counts as authoritative for now.
    return 1.0 if sources else 0.0


def _freshness_score(sources: list[Source]) -> float:
    # No document effective-date metadata yet (Phase 6). Always fresh until
    # ingest.py starts storing dates.
    return 1.0


def _reason_codes(
    intent: str,
    sources: list[Source],
    answer: str | None,
    missing: list[str],
    retrieval: float,
    entailment: float,
    freshness: float,
) -> list[str]:
    codes = []
    if intent == "out_of_scope":
        codes.append("OUT_OF_SCOPE")
    if not sources or retrieval < NO_POLICY_MATCH_THRESHOLD:
        codes.append("NO_POLICY_MATCH")
    if missing:
        codes.append("MISSING_SLOT")
    if answer and entailment < ENTAILMENT_THRESHOLD:
        codes.append("ANSWER_NOT_ENTAILED")
    if freshness < STALE_THRESHOLD:
        codes.append("STALE_DOCUMENT")
    if len(sources) >= 2:
        top, second = sources[0], sources[1]
        if (
            top.doc_id != second.doc_id
            and abs(top.score - second.score) < CONFLICT_SCORE_DELTA
        ):
            codes.append("CONFLICTING_SOURCES")
    return codes


def compute_confidence(
    intent: str,
    sources: list[Source],
    answer: str | None,
    missing_slots: list[str],
) -> tuple[float, dict[str, float], list[str]]:
    """Returns (confidence, breakdown, reason_codes)."""
    retrieval = _retrieval_score(sources)
    entailment = _entailment_score(answer, sources)
    slot = _slot_score(intent, missing_slots)
    authority = _authority_score(sources)
    freshness = _freshness_score(sources)

    breakdown = {
        "retrieval": retrieval,
        "answer_support": entailment,
        "slot_completeness": slot,
        "source_authority": authority,
        "freshness": freshness,
    }
    confidence = (
        RETRIEVAL_WEIGHT * retrieval
        + ENTAILMENT_WEIGHT * entailment
        + SLOT_WEIGHT * slot
        + AUTHORITY_WEIGHT * authority
        + FRESHNESS_WEIGHT * freshness
    )
    reason_codes = _reason_codes(
        intent, sources, answer, missing_slots, retrieval, entailment, freshness
    )
    return confidence, breakdown, reason_codes
