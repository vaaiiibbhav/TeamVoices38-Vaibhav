# CLAUDE.md

This file is read by Claude Code at the start of every session in this repo.
Keep it accurate — it is instructions, not documentation.

## What this project is

**CampusFlow AI** — a grounded Campus Helpdesk & Triage Agent. Students ask
questions about university policy; the agent answers only from official PDFs,
with a citation on every sentence. When it isn't sure, it asks or escalates
instead of guessing. When it wants to send an email or book a slot, a staff
member approves it first. Every decision is logged.

Full architecture: `docs/blueprint.pdf` (or ask — the phase-by-phase build
spec is `docs/build_spec.md`). This file is the compressed, always-loaded
version of that plan. If the two ever disagree, the blueprint wins; update
this file to match, don't improvise a third answer.

## The three non-negotiables

Every phase, every file, every shortcut gets checked against these. If a
change threatens one of them, stop and ask before proceeding.

1. **Every factual sentence carries a citation** — document, page, section.
   A post-processor strips any uncited sentence before it reaches the user.
   No exceptions for "obviously correct" answers.
2. **Confidence is computed, never self-reported.** A weighted composite of
   retrieval strength, answer entailment, slot completeness, source authority,
   and freshness. It routes control flow: ≥0.80 answer, 0.55–0.80 clarify,
   <0.55 triage. See `graph/confidence.py`.
3. **No side-effecting action executes without a human approval row in the
   database.** The executor accepts a `proposal_id` only, re-reads the
   approved payload from the DB, and verifies its hash. The model never has
   a code path to the send/execute call directly.

## Stack

- **Backend:** FastAPI, async, Python 3.11
- **Orchestration:** LangGraph — explicit `StateGraph`, conditional edges.
  Not the OpenAI Agents SDK, not Swarm (deprecated upstream).
- **LLM:** OpenAI-compatible endpoint, swappable by env var only.
  Groq (`llama-3.3-70b-versatile`) primary → OpenRouter free tier →
  Ollama (`llama3.1:8b`) offline fallback. Never hardcode a provider outside
  `llm/client.py`.
- **Embeddings:** `bge-small-en-v1.5`, local, CPU. No API key, no quota risk.
- **Vector store:** Qdrant (docker), pgvector as fallback.
- **Database:** Postgres. `traces`, `ticket_events`, `approvals` are
  append-only — never write an UPDATE or DELETE against them.
- **Memory:** TrueMemory (SQLite) for student profile + episodic recall only.
- **Frontend:** the `ui/` shell from `openai-cs-agents-demo`, backend fully
  replaced. The agent-trace sidebar is repurposed as the Inspector panel —
  don't rebuild it, re-point its data source.

## Where things live

```
services/api/graph/        LangGraph nodes, state, confidence, routing
services/api/rag/          ingest, search, prompts
services/api/gateway/      approval policy + propose/decide/execute
services/api/actions/      Composio (or SMTP fallback) — same gate either way
services/api/db/           models, migrations
apps/web/                  Next.js — chat console, admin console, inspector
data/seed_pdfs/            corpus for ingestion
data/golden_questions.yaml 25 eval questions with expected doc/page/band
```

## House rules

- **YAGNI.** No speculative helpers, factories, or config layers for features
  that don't exist yet.
- **Reuse before you write.** Check the relevant module above before adding
  a new file or function.
- **Stdlib and existing deps first.** Don't add a package for something
  `asyncio`, `json`, or a library already in `requirements.txt` handles.
- **Terse diffs.** Show the change, not a narrated tour of it. No
  restating what the code obviously does.
- **After any change to a graph node, schema, or route:** run
  `python -m py_compile <file>` and the relevant test in `tests/` before
  moving on. Don't let a broken gate carry into the next phase.
- **Confirm before generating a new file** in a phase you haven't started —
  one file or module at a time, not the whole phase at once.

## What NOT to do

- Don't reach for MCP servers to wrap **internal** function calls
  (`get_student_profile`, `get_exam_timetable`, etc.). MCP is for exposing
  tools to *external* clients. This is one FastAPI app calling its own
  Python functions — plain functions, not a server per domain.
- Don't add `ratel` or any tool-pruning layer yet. At ~12–15 tools the token
  savings are negligible; it's a Phase 7 stretch item at most, not
  infrastructure to build around.
- Don't drift into IT-helpdesk scope (WiFi resets, password resets,
  hardware tickets, cafeteria hours). The domain is campus operations:
  exams, attendance, OD/leave, hostel, fees, certificates, placement,
  library.
- Don't let the demo UI's Relevance/Jailbreak guardrails stand in for the
  confidence model — they're an input filter, not grounding. Keep both,
  don't conflate them.
- Don't generate a whole phase of files in one shot without confirming —
  see house rules.

## Current status

Update this section as you go — it's the one part of this file that's meant
to change daily.

- **Phase:** Phase 3 (Inspector) complete. Phase 4 (triage/tickets): DB layer
  (schema + migration) verified live 2026-07-29 — see below. Rest of Phase 4
  (triage/ticket nodes) not started. Not started: Phase 5 (approval gateway).
- **Last gate passed:** Phase 3 — `/dev-chat` renders all five sidebar
  components (`ConfidenceGauge`, `SourceCards`, `PathBreadcrumbs`,
  `ConversationContext`, `Guardrails`) against real live responses, not the
  `EMPTY_INSPECTOR` fallback: a slot-missing OD-leave question showed 71%
  confidence, a real per-component breakdown (0% slot completeness), the
  real retrieved source card, the real 5-node decision path ending at
  `clarify`, and exactly one reason code (`Missing Slot`) flagged amber
  while the other five showed neutral "Clear" — never a red "Failed." A
  slot-complete version of the same question showed 82%/`answer`, real
  `event_date`/`event_reason` slots in `ConversationContext`, and all six
  reason codes clear. `next_step_hint` ("Waiting on: event_date,
  event_reason") confirmed rendering live in `ConfidenceGauge` too — it was
  computed on the backend from the start but not wired into any component
  until this pass. Verified with screenshots, not a read-through.
- **Known broken / in progress:**
  - `ui/app/page.tsx` (the real ChatKit page, `AgentPanel`'s only current
    caller) still doesn't fetch or pass real `inspector` data — reworking
    it to do so is a separate, bigger task (it would need to stop using the
    Agents SDK streaming flow / `/chatkit/*` endpoints entirely, which
    404 against this backend already). `AgentPanel` accepts `agents` /
    `currentAgent` / `events` / `guardrails` props purely for backward
    compatibility with `page.tsx`'s existing call site — none of them are
    used internally anymore; drop them once `page.tsx` is reworked.
    `agent-panel.tsx` renders via an `EMPTY_INSPECTOR` fallback default in
    the meantime, verified visually to render cleanly (0%/Triage, empty
    sources/path/context, all six reason codes "Clear").
  - Quick-reply chips for clarifications (build_spec's Phase 3 render list)
    aren't built at all yet.
  - `services/api/main.py`'s `/api/chat/message` now calls
    `graph.build.app.ainvoke()` (plain request/response, not streaming —
    that's a separate later decision). Verified in the real browser at
    `/dev-chat`: the slot-present/slot-missing OD-leave pair produces
    `route: "answer"` vs `route: "clarify"` through the actual HTTP route.
  - `classify_intent` computes `missing_slots` but nothing branches on it
    until after `retrieve` + `evaluate` both run — a missing-slot question
    still pays for a full vector search and a full LLM answer-draft before
    being routed to `clarify`. Not fixed; a conditional edge straight from
    `classify_intent` would skip the wasted work.
  - `graph/build.py`'s `evaluate` node generates the cited answer itself
    (not the `answer` node) — confidence's answer-support component needs
    real entailment against a real answer, so the draft has to exist before
    the routing decision. The `answer` node is a thin pass-through.
  - `graph/build.py`'s `retrieve` node calls `search()` with `doc_types=None`
    (unfiltered) even though intent is now known — the indexed corpus is
    still one PDF tagged `exam_policy` only, so filtering by intent-as-doc_type
    would break retrieval for other intents until more docs are ingested
    with real per-intent `doc_type` coverage.
  - `propose_action` / `await_approval` nodes exist in `build.py` (per
    build_spec's Phase 2 node list) but aren't wired into any edge — no
    Phase 2 intent decides when a side-effecting action should be proposed;
    real wiring is Phase 5's approval gateway.
  - `clarify` / `triage` node messages are hardcoded templates, not
    LLM-generated — consistent with "hardcode anything that isn't
    retrieval."
  - `graph/confidence.py`'s `source_authority` and `freshness` components
    are placeholder constants (1.0 always) — no per-document trust tiers or
    effective-date metadata exist yet. `STALE_DOCUMENT` and
    `CONFLICTING_SOURCES` reason codes have real trigger logic but can't
    actually fire against the current single-doc corpus; real exercise
    waits on Phase 6's superseded-circular golden question.
  - ChatKit UI (`ui/components/chatkit-panel.tsx`, `agent-panel.tsx`) is
    still the unmodified airline demo — real chat UI + Inspector panel is
    deferred to Phase 3, not started. `dev-chat` is a throwaway test page,
    not the real frontend.
  - Docker Desktop is running on this dev machine as of 2026-07-29 —
    `docker compose up -d` brings up `postgres:16` and `qdrant/qdrant`.
    Qdrant still runs in `qdrant-client`'s embedded on-disk mode
    (`services/api/qdrant_data/`, gitignored) because `QDRANT_URL` in
    `.env` is still empty — the docker Qdrant container is up but unused
    until that's set to `http://localhost:6333`.
  - **Postgres/migration — verified live 2026-07-29.** `alembic upgrade
    head` applied `dbaea2ba8ac2` (initial schema) against the real
    docker-compose Postgres, not just `py_compile`. Confirmed via
    `information_schema.tables`: all 11 schema tables present
    (`documents`, `doc_chunks`, `students`, `staff`, `conversations`,
    `traces`, `messages`, `tickets`, `ticket_events`, `approvals`,
    `corrections`) plus `alembic_version`. Append-only trigger confirmed
    firing for real, not just read from the migration source: inserted a
    row into `traces`, then both `UPDATE` and `DELETE` against it raised
    `<table> is append-only: <OP> not allowed` from
    `reject_update_delete()`, and the row was unchanged after both
    attempts. Same trigger is bound to `ticket_events` and `approvals`.
  - **The real venv is `campus-helpdesk-agent\venv\`** (this repo root),
    not `..\.venv\` one level up at the `Campus Helpdesk Triage Agent\`
    parent folder — that one's a stray empty venv from earlier setup,
    still present as of 2026-07-29, and running anything against it fails
    with missing packages. `dev:server` below always launches the correct
    one automatically, so this only bites you running uvicorn/alembic/pip
    by hand — check you're pointing at `venv\Scripts\` inside
    `campus-helpdesk-agent\` first if a manual command can't find a
    package that's clearly installed.
  - `ui/package.json`'s `dev:server` script — fixed 2026-07-29. Was
    pointing at the deleted `python-backend/`. Now
    `cd .. && venv\Scripts\python.exe -m uvicorn services.api.main:app
    --reload --host 0.0.0.0 --port 8000`, run from `ui/`. Two things that
    bit us getting here, worth knowing if this breaks again: (1)
    `main.py` uses absolute imports (`from services.api.graph...`), so
    uvicorn must be launched with the repo root as cwd, not from inside
    `services/api/`; (2) npm's default Windows script-shell is `cmd.exe`,
    which won't resolve a relative executable path with forward slashes
    as the command token (`venv/Scripts/python.exe` fails with `'venv' is
    not recognized`) — needs backslashes. `npm run dev` from `ui/` now
    starts both servers standalone, verified from a fresh shell (not just
    the ad hoc background commands used earlier).
  - `data/seed_pdfs/examination_regulations_PLACEHOLDER.pdf` is synthetic,
    flagged in the file itself, needs replacing with real university PDFs
    before the demo.