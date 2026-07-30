"""Builds the Inspector payload the frontend renders. Raw reason codes are
sent as-is — the frontend (guardrails.tsx) owns the human-readable mapping,
the same way it already translated airline guardrail codes to display names.
build_spec's "human strings, never raw enums" is a rendering rule, not a
wire-format rule: the UI must never *show* NO_POLICY_MATCH on screen, but the
raw code has to travel over the API so the UI can tell which of the six
fired.
"""
from __future__ import annotations

from pydantic import BaseModel

from services.api.graph.state import AgentState
from services.api.rag.schemas import Source


class InspectorPayload(BaseModel):
    trace_id: str
    confidence: float
    breakdown: dict[str, float]
    reason_codes: list[str]
    next_step_hint: str
    route: str
    path: list[str]
    intent: str | None
    slots: dict[str, str]
    sources: list[Source]
    latency_ms: float
    pending_approval: bool
    ticket_id: str | None
    proposal_id: str | None


def _next_step_hint(state: AgentState) -> str:
    route = state["route"]
    if route == "answer":
        return "Answer delivered."
    if route == "clarify":
        if state["missing_slots"]:
            return "Waiting on: " + ", ".join(state["missing_slots"])
        return "Ask the student to rephrase or add detail."
    if route == "triage":
        return "Escalated to staff for manual review."
    return ""


def build_inspector_payload(state: AgentState, latency_ms: float) -> InspectorPayload:
    return InspectorPayload(
        trace_id=state["trace_id"],
        confidence=state["confidence"],
        breakdown=state["confidence_breakdown"],
        reason_codes=state["reason_codes"],
        next_step_hint=_next_step_hint(state),
        route=state["route"],
        path=state["path"],
        intent=state["intent"],
        slots=state["slots"],
        sources=state["sources"],
        latency_ms=latency_ms,
        pending_approval=state["pending_approval"],
        ticket_id=state["ticket_id"],
        proposal_id=state["proposal_id"],
    )
