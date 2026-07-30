"""Shared RAG data shapes.

Frozen early: graph/state.py (Phase 2) and the chat route both depend on this
exact structure, even though only rag/search.py imports it today.

This Source is canonical. When graph/state.py is built in Phase 2, import it
from here — do not redeclare a TypedDict version of it there.
"""
from __future__ import annotations

from pydantic import BaseModel


class Source(BaseModel):
    doc_id: str
    doc_title: str
    page: int
    section: str
    snippet: str
    score: float
    header: str
