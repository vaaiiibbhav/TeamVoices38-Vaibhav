"""The StateGraph. Conditional edges: missing slots -> clarify;
conf >= 0.80 -> answer; 0.55-0.80 -> clarify; < 0.55 -> triage.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from langgraph.graph import END, StateGraph

from services.api.db.tickets import create_ticket
from services.api.gateway.approval import propose
from services.api.graph.confidence import compute_confidence
from services.api.graph.routing import SLA_HOURS, compute_priority, route_department
from services.api.graph.slots import CAMPUS_INTENTS, missing_slots
from services.api.graph.state import AgentState
from services.api.llm.client import complete
from services.api.rag.postprocess import enforce_citations
from services.api.rag.prompts import INSUFFICIENT_CONTEXT, build_answer_messages
from services.api.rag.search import search

CLASSIFY_SYSTEM_PROMPT = f"""Classify the student's question into exactly one \
campus intent and extract any slot values explicitly present in the question.

Intents: {", ".join(CAMPUS_INTENTS)}

Known slots per intent:
- od_leave_request: event_date, event_reason
- hostel_issue: issue_type
- certificate_request: certificate_type

Respond with ONLY JSON, no other text: \
{{"intent": "<intent>", "slots": {{"<slot_name>": "<value>", ...}}}}
Only include a slot if its value is explicitly stated in the question."""


def step(state: AgentState, node_name: str, **updates) -> AgentState:
    return {**state, **updates, "path": state["path"] + [node_name]}


def initial_state(question: str, trace_id: str) -> AgentState:
    return AgentState(
        trace_id=trace_id,
        question=question,
        profile={},
        intent=None,
        slots={},
        missing_slots=[],
        sources=[],
        confidence=0.0,
        confidence_breakdown={},
        reason_codes=[],
        route=None,
        path=[],
        answer=None,
        pending_approval=False,
        ticket_id=None,
        proposal_id=None,
    )


async def load_context(state: AgentState) -> AgentState:
    return step(state, "load_context", profile={})


async def classify_intent(state: AgentState) -> AgentState:
    messages = [
        {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
        {"role": "user", "content": state["question"]},
    ]
    raw = await complete(messages, json_mode=True)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {}

    intent = parsed.get("intent")
    if intent not in CAMPUS_INTENTS:
        intent = "general_info"

    raw_slots = parsed.get("slots")
    slots = (
        {k: v for k, v in raw_slots.items() if isinstance(v, str) and v.strip()}
        if isinstance(raw_slots, dict)
        else {}
    )

    return step(
        state,
        "classify_intent",
        intent=intent,
        slots=slots,
        missing_slots=missing_slots(intent, slots),
    )


async def retrieve(state: AgentState) -> AgentState:
    sources = search(state["question"], None, 5)
    return step(state, "retrieve", sources=sources)


async def evaluate(state: AgentState) -> AgentState:
    """Drafts the cited answer here (not in the answer node) — confidence's
    answer-support component needs real entailment against a real answer, or
    the >=0.80 band would be structurally unreachable pre-answer."""
    sources = state["sources"]
    messages = build_answer_messages(state["question"], sources)
    raw_answer = await complete(messages)
    draft_answer, cited_sources = enforce_citations(raw_answer, sources)
    final_answer = None if draft_answer == INSUFFICIENT_CONTEXT else draft_answer

    confidence, breakdown, reason_codes = compute_confidence(
        state["intent"], sources, final_answer, state["missing_slots"]
    )
    return step(
        state,
        "evaluate",
        answer=final_answer,
        sources=cited_sources or sources,
        confidence=confidence,
        confidence_breakdown=breakdown,
        reason_codes=reason_codes,
    )


def route_after_evaluate(state: AgentState) -> str:
    if state["missing_slots"]:
        return "clarify"
    if state["confidence"] >= 0.80:
        return "answer"
    if state["confidence"] >= 0.55:
        return "clarify"
    return "triage"


async def answer(state: AgentState) -> AgentState:
    return step(state, "answer", route="answer")


async def clarify(state: AgentState) -> AgentState:
    if state["missing_slots"]:
        message = (
            "Could you provide the following before I continue: "
            + ", ".join(state["missing_slots"])
            + "?"
        )
    else:
        message = (
            "I'm not confident enough in the available policy documents to "
            "answer that fully. Could you rephrase or add more detail?"
        )
    return step(state, "clarify", route="clarify", answer=message)


async def triage(state: AgentState) -> AgentState:
    intent = state["intent"] or "general_info"
    department = route_department(intent)
    priority = compute_priority(intent)
    sla_due_at = datetime.now(timezone.utc) + timedelta(hours=SLA_HOURS[priority])
    ticket_id = await create_ticket(
        intent=intent,
        department=department,
        priority=priority,
        subject=f"[{intent}] {state['question'][:80]}",
        description=state["question"],
        sla_due_at=sla_due_at,
    )
    ticket_ref = f"TKT-{ticket_id[:8].upper()}"
    message = (
        "I can't confidently answer this from the indexed policies. "
        f"This has been flagged for staff review — your request has been "
        f"logged as ticket {ticket_ref}."
    )
    return step(
        state, "triage", route="triage", answer=message, ticket_id=ticket_id
    )


def route_after_triage(state: AgentState) -> str:
    """od_leave_request can only reach triage with event_date/event_reason
    already present — route_after_evaluate sends any missing-slot question
    to clarify first. The explicit slot check documents that invariant
    instead of relying on it silently."""
    if state["intent"] == "od_leave_request" and state["slots"].get("event_date"):
        return "propose_action"
    return "end"


async def propose_action(state: AgentState) -> AgentState:
    payload = {
        "ticket_id": state["ticket_id"],
        "department": route_department(state["intent"]),
        "event_date": state["slots"].get("event_date"),
        "event_reason": state["slots"].get("event_reason"),
    }
    proposal_id = await propose(
        action_type="calendar_event", ticket_id=state["ticket_id"], payload=payload
    )
    return step(state, "propose_action", proposal_id=proposal_id)


async def await_approval(state: AgentState) -> AgentState:
    return step(state, "await_approval", pending_approval=True)


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_context", load_context)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve", retrieve)
    graph.add_node("evaluate", evaluate)
    graph.add_node("answer", answer)
    graph.add_node("clarify", clarify)
    graph.add_node("triage", triage)
    graph.add_node("propose_action", propose_action)
    graph.add_node("await_approval", await_approval)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "classify_intent")
    graph.add_edge("classify_intent", "retrieve")
    graph.add_edge("retrieve", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"answer": "answer", "clarify": "clarify", "triage": "triage"},
    )
    graph.add_edge("answer", END)
    graph.add_edge("clarify", END)
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {"propose_action": "propose_action", "end": END},
    )
    graph.add_edge("propose_action", "await_approval")
    graph.add_edge("await_approval", END)

    return graph.compile()


app = build_graph()
