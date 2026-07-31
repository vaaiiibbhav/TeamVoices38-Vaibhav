# CampusFlow AI

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A grounded Campus Helpdesk & Triage Agent. Students ask questions about
university policy — exams, attendance, OD/leave, hostel, fees, certificates,
placement, library — and get answers sourced only from official PDFs, with a
citation on every sentence. When the agent isn't confident, it asks a
clarifying question or escalates to a staff ticket instead of guessing. When
it wants to take an action (send an email, book a slot), a staff member has
to approve it first — the model never has a direct path to the send/execute
call.

## Why it's built this way

- **Every factual sentence carries a citation** — document, page, section. A
  post-processor strips any uncited sentence before it reaches the student.
- **Confidence is computed, never self-reported.** A weighted composite of
  retrieval strength, answer entailment, slot completeness, source
  authority, and freshness routes control flow: high confidence answers,
  medium confidence clarifies, low confidence escalates to a human.
- **No side-effecting action executes without a human approval row in the
  database.** The executor only ever accepts a `proposal_id`, re-reads the
  approved payload, and verifies its hash.

## Stack

- **Backend:** FastAPI (async, Python 3.11), orchestrated with an explicit
  LangGraph `StateGraph`
- **LLM:** any OpenAI-compatible endpoint, swappable by env var — Groq
  primary, OpenRouter/Ollama as fallbacks
- **Embeddings:** `bge-small-en-v1.5`, local, CPU-only
- **Vector store:** Qdrant
- **Database:** Postgres (append-only `traces` / `ticket_events` / `approvals`)
- **Frontend:** Next.js — chat console, admin console, and an inspector
  panel for the confidence/routing trace

## Running it locally

```bash
# 1. Bring up Postgres + Qdrant
docker compose up -d

# 2. Backend: create the venv at the repo root (this exact path matters —
#    there's a stray empty venv one level up that will NOT have the deps)
python -m venv venv
venv\Scripts\pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

# 3. Copy .env.example to .env and fill in your LLM provider's API key

# 4. Frontend + backend together
cd ui
npm install
npm run dev
```

`npm run dev` starts both the Next.js dev server (`localhost:3000`) and the
FastAPI backend (`localhost:8000`) via `concurrently`. To run the backend on
its own instead:

```bash
venv\Scripts\python.exe -m uvicorn services.api.main:app --reload --port 8000
```

Run from the repo root, not `services/api/` — the app uses absolute imports.

## Attribution

The Next.js UI shell insipired by llm.
Everything else — the FastAPI backend, the LangGraph orchestration, the RAG
pipeline, the confidence model, the approval gateway, the admin console, and
the domain logic throughout — is original to this project.

