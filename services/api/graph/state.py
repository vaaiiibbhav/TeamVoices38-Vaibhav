"""The AgentState TypedDict. Freeze this — every graph node and the Phase 3
Inspector payload build against this exact shape.
"""
from __future__ import annotations

from typing import TypedDict

from services.api.rag.schemas import Source


class AgentState(TypedDict):
    trace_id: str
    question: str
    profile: dict

    intent: str | None
    slots: dict[str, str]
    missing_slots: list[str]

    sources: list[Source]

    confidence: float
    confidence_breakdown: dict[str, float]
    reason_codes: list[str]

    route: str | None
    path: list[str]

    answer: str | None
    pending_approval: bool
    ticket_id: str | None
