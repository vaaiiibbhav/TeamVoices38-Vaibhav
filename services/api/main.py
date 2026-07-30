"""POST /api/chat/message runs the full LangGraph pipeline. Plain
request/response for now — streaming is a separate later decision."""
from __future__ import annotations

import time
import uuid

from dotenv import load_dotenv

load_dotenv()

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.api.db.tickets import list_tickets
from services.api.gateway.approval import decide, execute, list_pending
from services.api.graph.build import app as agent_graph
from services.api.graph.build import initial_state
from services.api.graph.inspector import InspectorPayload, build_inspector_payload

app = FastAPI(title="CampusFlow AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str | None
    ticket_id: str | None
    proposal_id: str | None
    inspector: InspectorPayload


@app.post("/api/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest) -> ChatResponse:
    state = initial_state(request.message, trace_id=str(uuid.uuid4()))
    start = time.perf_counter()
    result = await agent_graph.ainvoke(state)
    latency_ms = (time.perf_counter() - start) * 1000

    return ChatResponse(
        answer=result["answer"],
        ticket_id=result["ticket_id"],
        proposal_id=result["proposal_id"],
        inspector=build_inspector_payload(result, latency_ms),
    )


@app.get("/api/admin/tickets")
async def admin_tickets(
    department: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> list[dict]:
    tickets = await list_tickets(
        department=department, priority=priority, status=status
    )
    return [
        {**t, "id": str(t["id"]), "sla_due_at": t["sla_due_at"].isoformat(),
         "created_at": t["created_at"].isoformat()}
        for t in tickets
    ]


class DecideRequest(BaseModel):
    approved: bool
    staff_id: str | None = None


@app.get("/api/approvals")
async def approvals_pending() -> list[dict]:
    rows = await list_pending()
    return [
        {
            "proposal_id": str(r["proposal_id"]),
            "ticket_id": str(r["ticket_id"]) if r["ticket_id"] else None,
            "action_type": r["action_type"],
            "risk_tier": r["risk_tier"],
            "payload": json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@app.post("/api/approvals/{proposal_id}/decide")
async def approvals_decide(proposal_id: str, request: DecideRequest) -> dict:
    try:
        status = await decide(
            proposal_id=proposal_id, approved=request.approved, staff_id=request.staff_id
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"proposal_id": proposal_id, "status": status}


@app.post("/api/approvals/{proposal_id}/execute")
async def approvals_execute(proposal_id: str) -> dict:
    try:
        result = await execute(proposal_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"proposal_id": proposal_id, "result": result}
