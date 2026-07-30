"""POST /api/chat/message runs the full LangGraph pipeline. Plain
request/response for now — streaming is a separate later decision."""
from __future__ import annotations

import time
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    inspector: InspectorPayload


@app.post("/api/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest) -> ChatResponse:
    state = initial_state(request.message, trace_id=str(uuid.uuid4()))
    start = time.perf_counter()
    result = await agent_graph.ainvoke(state)
    latency_ms = (time.perf_counter() - start) * 1000

    return ChatResponse(
        answer=result["answer"],
        inspector=build_inspector_payload(result, latency_ms),
    )
