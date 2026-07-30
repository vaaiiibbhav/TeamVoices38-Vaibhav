# CampusFlow AI — Build Spec for Claude Code

You are implementing a **grounded** Campus Helpdesk & Triage Agent. Read this whole
file before writing code. Confirm each file creation with me before moving to the
next phase.

## Non-negotiables

These three properties are the product. If a decision threatens one of them, stop
and ask:

1. **Every factual sentence carries a citation** (document, page, section). Uncited
   sentences are stripped before display.
2. **Confidence is a computed composite**, never an LLM self-report, and it routes
   control flow deterministically.
3. **No side-effecting action executes without a human approval row** written to the
   database. The executor takes a `proposal_id`, never a model-supplied payload.

## Stack

- **Backend:** FastAPI (async, Python 3.11)
- **Orchestration:** LangGraph — explicit `StateGraph`, conditional edges
- **LLM:** OpenAI-compatible endpoint. Groq (`llama-3.3-70b-versatile`) primary,
  OpenRouter free tier secondary, Ollama (`llama3.1:8b`) offline fallback.
  One client wrapper, provider swappable by env var. No provider-specific code
  anywhere else.
- **Embeddings:** `BAAI/bge-small-en-v1.5`, local, CPU. No API, no quota.
- **Vector store:** Qdrant (docker). pgvector fallback.
- **Database:** Postgres
- **Memory:** TrueMemory (SQLite) for student profile only
- **Frontend:** the `ui/` directory from the cloned demo, backend swapped out

Not in scope: `ratel`, MCP servers for internal tools, Swarm (deprecated), any
IT-helpdesk domain (WiFi, passwords, hardware, cafeteria).

---

## Phase 0 — Strip the clone (30 min)

1. Verify `ui/` runs standalone: `cd ui && npm install && npm run dev`.
2. Delete `python-backend/` entirely.
3. Locate the agent-trace sidebar component. Note its props — this becomes the
   Inspector panel. Do not rebuild it; re-point its data source.
4. Scaffold `services/api/` and a `docker-compose.yml` with Postgres + Qdrant.
5. `.env.example`: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `DATABASE_URL`,
   `QDRANT_URL`, `EMBED_MODEL`, `CONF_ANSWER_THRESHOLD=0.80`,
   `CONF_CLARIFY_THRESHOLD=0.55`, `TRUEMEMORY_DB_PATH`, `AUTO_APPROVE_MAX_RISK=low`.

**Gate:** frontend renders with a mocked inspector payload. Do not proceed until true.

---

## Phase 1 — Vertical slice: question in, cited answer out (2 hrs)

The single most important phase. Hardcode anything that isn't retrieval.

1. `rag/ingest.py`: PyMuPDF parse per page → regex section labels → 700-token chunks
   with 120 overlap, never crossing a page boundary → **prepend the citation header**
   `[<title> | p.<n> | <section>]` to each chunk before embedding → index in Qdrant
   with full metadata in the payload.
2. `rag/search.py`: `search(query, doc_types, k) -> list[Source]`. Dense only for now.
3. `rag/prompts.py`: the constrained answer prompt. Hard rules — use only the numbered
   CONTEXT blocks; every factual sentence ends with `[n]`; if the context is
   insufficient reply exactly `INSUFFICIENT_CONTEXT`; never invent a page, section,
   office, deadline, or email.
4. Post-processor: strip any sentence lacking an `[n]` marker. If everything is
   stripped, treat as `INSUFFICIENT_CONTEXT`.
5. `POST /api/chat/message` → returns answer + sources. Wire to the UI.

**Gate:** ask a real question against a real PDF, get a real answer with a real page
number, rendered in the browser.

---

## Phase 2 — The graph (2 hrs)

1. `graph/state.py` — the `AgentState` TypedDict. Freeze this; everyone builds
   against it.
2. `graph/slots.py` — required slots per intent. Campus intents only:
   `exam_policy`, `attendance_query`, `od_leave_request`, `hostel_issue`,
   `fee_scholarship`, `certificate_request`, `placement_query`, `library_query`,
   `general_info`, `out_of_scope`.
3. `graph/confidence.py` — weighted composite: retrieval 0.40, answer support 0.30,
   slot completeness 0.15, source authority 0.10, freshness 0.05. Emit reason codes:
   `NO_POLICY_MATCH`, `MISSING_SLOT`, `ANSWER_NOT_ENTAILED`, `CONFLICTING_SOURCES`,
   `STALE_DOCUMENT`, `OUT_OF_SCOPE`. Use token-overlap for entailment initially;
   upgrade to an NLI model only if time allows.
4. `graph/build.py` — nodes: `load_context`, `classify_intent`, `retrieve`,
   `evaluate`, `answer`, `clarify`, `triage`, `propose_action`, `await_approval`.
   Conditional edges: missing slots → clarify; conf ≥ 0.80 → answer;
   0.55–0.80 → clarify; < 0.55 → triage.

**Gate:** the same question routes differently when you remove a required slot.

---

## Phase 3 — Inspector panel (2 hrs)

Build this before tickets. It is the scoring surface.

Emit the inspector payload: `trace_id`, `confidence`, per-component `breakdown`,
`reason_codes`, `next_step_hint`, `route`, `path` (node sequence), `intent`, `slots`,
`sources`, `latency_ms`, `pending_approval`.

Render: confidence meter banded at 0.55/0.80 with the number visible; reason codes as
human strings, never raw enums; source cards with title/page/section/snippet;
decision-path breadcrumbs; quick-reply chips for clarifications.

**If you build one extra thing all weekend, make it the citation deep-link** — clicking
a source opens the actual PDF at that page.

---

## Phase 4 — Triage, tickets, admin queue (2 hrs)

1. Full DDL: `documents`, `doc_chunks`, `students`, `staff`, `conversations`,
   `messages`, `traces`, `tickets`, `ticket_events`, `approvals`, `corrections`.
   `traces`, `ticket_events`, `approvals` are append-only.
2. `graph/routing.py` — a plain dict, not an LLM call. Intent → department:
   Examination Cell, Academic Office, Hostel Administration, Accounts & Finance,
   Placement Cell, Library, Student Services.
3. Priority: URGENT (deadline < 24h or blocks exam/scholarship, 1h SLA),
   HIGH (< 7 days or residence/safety, 8h), MEDIUM (administrative, 2 days),
   LOW (informational, 5 days).
4. Admin ticket table with filters and a live SLA countdown. Seed 8 tickets so it
   never looks empty.

---

## Phase 5 — Approval gateway (2 hrs) — the differentiator

1. `gateway/policy.py` — risk tiers. Low (auto): answer, create ticket, draft email.
   Medium (approval): calendar event, close/reprioritise ticket. High (approval):
   send email as the office, anything touching grades or fees.
2. `gateway/approval.py` — `propose()` writes a PENDING row with a `payload_hash`.
   `decide()` records the staff decision. `execute()` **takes only a `proposal_id`,
   re-reads the approved payload from the database, and verifies the hash.** The model
   must have no path to the execution call.
3. Approval inbox in the admin UI with the rendered payload preview, pushed live.
4. Wire clawvisor as the policy layer if it integrates in under an hour. If not, this
   module *is* the gateway — same schema, same story, ship it.

**Gate:** propose → PENDING → staff approves → executes → result written back.

---

## Phase 6 — Freeze, then calibrate

Stop adding features. Then:

1. `data/golden_questions.yaml` — 25 questions with expected intent, document, page,
   and confidence band. Include an out-of-scope question and a question covered by a
   deliberately superseded circular (to trigger `CONFLICTING_SOURCES`).
2. `scripts/eval_retrieval.py` — recall@5 and citation accuracy. Record the numbers.
3. Tune thresholds so each demo question lands in its intended band.
4. `tests/test_gateway.py` — assert a high-risk action can never auto-execute.

---

## Phase 7 — Optional, only if everything above is done

Composio for Gmail/Calendar (SMTP fallback behind the same gate if OAuth fights you),
hybrid BM25 + reranking, `ratel` tool pruning, the admin-correction learning loop,
Pathway live re-index.

---

## Working rules

- Confirm each file with me before the next one.
- Never let a phase gate slip. If a gate fails, fix it before proceeding.
- If you find yourself adding a dependency not listed above, stop and ask why.
