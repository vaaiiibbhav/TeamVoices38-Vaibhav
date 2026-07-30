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
- **This corpus is VIT Bhopal, B.Tech CSE (the "BCE" programme) specifically**
  — the OD contact email, curriculum PDF, and fee/attendance figures are all
  BCE-scoped. Other branches and M.Tech are out of scope for this build; that's
  a stated corpus boundary, not something the agent should imply full coverage
  of by answering confidently for other programmes.
- **`od_leave_request`'s slot schema assumes every question in that intent is
  a leave submission** — `slots.py`'s `REQUIRED_SLOTS["od_leave_request"] =
  ["event_date", "event_reason"]` applies unconditionally, even to a pure
  policy-lookup question ("which email do I use, is there a cap") that isn't
  filing anything. `route_after_evaluate` checks `missing_slots` before
  confidence, so these questions get diverted to `clarify`'s hardcoded
  no-citation template without ever reaching the cited answer. Traced
  2026-07-30 (see below) — not fixed. Don't add more OD-leave golden
  questions phrased as policy lookups without knowing this will misroute
  them; if you fix this, it needs the intent split into two shapes (lookup
  vs. actual request) or a way to tell them apart before slot-gating.
- Don't let the demo UI's Relevance/Jailbreak guardrails stand in for the
  confidence model — they're an input filter, not grounding. Keep both,
  don't conflate them.
- Don't generate a whole phase of files in one shot without confirming —
  see house rules.

## Current status

Update this section as you go — it's the one part of this file that's meant
to change daily.

- **Phase:** Phase 3 (Inspector) and Phase 4 (triage/tickets) complete.
  Phase 5 (approval gateway) complete as of 2026-07-29 — `gateway/policy.py`
  risk tiers, `gateway/approval.py`'s propose/decide/execute (proposal_id-
  only executor, payload-hash verified, append-only event ledger),
  `triage` → `propose_action` wiring for `od_leave_request` →
  `calendar_event`, HTTP routes (`GET /api/approvals`, `POST /api/approvals/
  {id}/decide`, `POST /api/approvals/{id}/execute`), and a bare approval
  inbox at `/admin/approvals` — all browser/live-verified, not read-through
  (see gate below). Deliberately out of scope for Phase 5 (not blockers,
  named in build_spec as later phases): no real Composio/SMTP execution
  (`_run_action` in `approval.py` simulates and returns a result dict —
  Phase 7); no staff auth on any `/admin/*` route or `/api/approvals/*`
  (`decided_by` is always `null` — same gap as `/admin` tickets); only one
  action type (`calendar_event`) is ever proposed — `send_email`/
  `grade_change`/`fee_change` exist in `policy.py`'s risk table for
  completeness against the blueprint but nothing calls them.
- **Last gate passed:** Phase 5 — proposed via a real `/api/chat/message`
  call (an off-corpus `od_leave_request` question landed at 0.548
  confidence, routed `triage`, created a real `tickets` row, then
  `propose_action` wrote a real `approvals` PENDING row with a real
  `calendar_event` payload). Approved and executed **from an actual
  browser**, not a script: navigated to `/admin/approvals`, saw 5 real
  PENDING proposals render, clicked Approve on one — it called `decide()`
  then `execute()` for real, the row vanished from the inbox (5→4), and
  `psql` confirmed three real append-only rows for that `proposal_id`
  (PENDING → APPROVED → EXECUTED with a `result`). Clicked Reject on a
  second proposal — vanished (4→3), `psql` confirmed PENDING → REJECTED
  with no `execute` call and no `result`. Browser console clean, zero
  errors, across both clicks. Guardrails also exercised directly (not just
  the happy path): `decide()` on an already-`EXECUTED` proposal raises
  `ValueError`; `execute()` on a still-`PENDING` (never-approved) proposal
  raises `ValueError` — the non-negotiable ("no side-effecting action
  executes without a human approval row") holds under misuse, not just
  the intended sequence.
  **Reload gotcha hit and fixed mid-session:** the `--reload` uvicorn dev
  server silently stopped picking up file changes — worker process was
  1+ hour stale despite edits, so an early triage-routed test ran against
  pre-Phase-5 code and (correctly, given stale code) showed no
  `propose_action` in the path. Fixed by killing the whole reloader+worker
  process tree and relaunching. Don't trust `--reload` on this Windows
  setup without checking the worker's actual start time against your last
  edit if a change doesn't seem to take effect.
  **Corpus note:** getting a real `od_leave_request` question below 0.55
  confidence took several rephrasing attempts — the single-doc corpus's
  Chapter 6 (OD Leave) is semantically sticky, so most OD phrasings land in
  `answer` or `clarify`, not `triage`. Not a bug, same single-doc-corpus
  limitation already tracked below for Phase 6.
- **Previous gate:** Phase 4 — `/admin` browser-verified live 2026-07-29
  via Playwright MCP (see full detail below): SLA countdown re-renders
  live off the 1s interval (confirmed two snapshots apart, e.g. `OVERDUE by
  2h 54m` → `2h 55m`), department/priority/status filters actually refetch
  and narrow the result set (not just render — selecting "Hostel
  Administration" cut 10 tickets to 3, all matching), priority badge color
  matches real priority value across every row (URGENT=red destructive,
  HIGH=blue primary, MEDIUM=gray secondary, LOW=outline, checked via
  computed styles on all 10 rows, no mismatches), and the closed-but-
  past-due seed ticket renders `closed (was 1d 0h late)` in muted gray, not
  the red `OVERDUE` treatment used for open tickets. Also fixed and
  reverified in the same pass: initial page load flashed `0 tickets / No
  tickets match these filters` for one frame before the fetch resolved,
  because `loading` started `false` and only flipped `true` inside the
  data-fetching `useEffect`. Changed to `useState(true)` — first paint now
  shows `Loading...` instead of the misleading empty state, confirmed by
  re-navigating and snapshotting immediately post-navigation.
- **Earlier gate:** Phase 3 — `/dev-chat` renders all five sidebar
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
  - `propose_action` / `await_approval` nodes — wired 2026-07-29 (Phase 5,
    see gate above). `triage` conditionally routes to `propose_action` only
    for `intent == "od_leave_request" and slots.get("event_date")`; every
    other triage path still goes straight to `END`. Only one action type is
    ever proposed this way (`calendar_event`) — no other intent/node
    proposes an action yet.
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
  - **Ticket creation + admin dashboard — added 2026-07-29.** New:
    `services/api/db/pool.py` (asyncpg pool), `services/api/db/tickets.py`
    (`create_ticket`/`list_tickets`, raw SQL — no ORM, matches migrations),
    `services/api/db/seed_tickets.py` (8 fake tickets spanning every
    department/priority/status, one overdue, one imminent, one closed-but-
    past-due to confirm closed tickets don't alarm), `ui/app/admin/page.tsx`
    (department/priority/status filters, client-side live SLA countdown
    ticking every second off `sla_due_at`). `graph/build.py`'s `triage`
    node now calls `routing.route_department` / `compute_priority` and
    inserts a real `tickets` row (`AgentState` gained `ticket_id`) instead
    of just computing an unused department string. Verified live, not just
    read-through: sent a hostel-issue question through the real
    `/api/chat/message` route (only doc in the corpus is exam policy, so
    confidence bottomed out) — response routed `triage`, and `psql`
    confirmed a new `tickets` row with `department = 'Hostel
    Administration'`, `priority = 'MEDIUM'`, `sla_due_at` = created +48h,
    matching `routing.py`'s mapping and `SLA_HOURS`. `GET
    /api/admin/tickets` (with department/priority/status query params)
    verified via curl directly and through the Next.js `/api/:path*` proxy,
    both returning real seeded + live-created rows. `tests/test_routing.py`
    added as a plain-assert self-check on the department/priority mapping
    (no pytest in this venv; run with `python tests/test_routing.py`).
    **Browser-verified 2026-07-29** via Playwright MCP once it reconnected
    — see the Phase 4 gate note above for the specific checks (live
    countdown, working filters, correct badge colors, closed-ticket
    handling, loading-state fix). `/admin` and `/api/admin/tickets` still
    have no auth — anyone who can reach the backend can list tickets; not
    a blocker for Phase 4, tracked as a gap above.
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
  - **Real corpus swapped in 2026-07-29.** `examination_regulations_PLACEHOLDER.pdf`
    renamed to `.pdf.bak` (kept, not deleted) and excluded from ingestion.
    Real corpus is now 7 files: two pasted-in real PDFs
    (`Curriculum_Student_BTECH-BCE-2023_23BCE11700_...pdf`,
    `Mini-Brochure-2026.pdf`) plus five PDFs authored from
    `data/vitbhopal_raw/` source material (VIT Bhopal screenshots + a raw
    text dump) in the same title/chapter/clause structure as the old
    placeholder: `examination_services.pdf`, `library_services.pdf`,
    `hostel_facilities.pdf`, `placement_and_training.pdf`,
    `academic_system_ffcs.pdf`. Deliberately excluded from the corpus:
    marketing/leadership-bio content and a campus-life card page (no
    citable policy value), and a VTOP screenshot of one specific logged-in
    student's live attendance/CGPA (personal academic data, not official
    policy — wrong thing to embed as a "citable source").
    Re-ingested against the local embedded Qdrant store (wiped
    `services/api/qdrant_data/` first so no stale placeholder-only vectors
    lingered): **19 chunks total** — `examination_services.pdf` 2,
    `library_services.pdf` 1, `hostel_facilities.pdf` 3,
    `placement_and_training.pdf` 4, `academic_system_ffcs.pdf` 1,
    the curriculum PDF 8, `Mini-Brochure-2026.pdf` **0**.
    Section-label smoke test: all 11 chunks from the 5 authored docs landed
    with real `Chapter N — Title` section labels (verified via direct
    Qdrant payload scroll, not just eyeballing the PDFs) — zero `General`
    defaulting there. Two real findings, not fixed, just reported per this
    task's scope: (1) the curriculum PDF's 8 chunks **all** land as
    `General` — it's a VTOP tabular data export ("CREDIT INFO", per-course
    tables), not chaptered prose, so `ingest.py`'s
    `Chapter\s+\d+\s*[—-]\s*.+` regex has nothing to match; this is a real
    gap in section-label coverage for tabular documents, not a bug in the
    regex itself. (2) `Mini-Brochure-2026.pdf` is a fully scanned/image-only
    PDF — `page.get_text()` returns 0 characters on all 12 pages, so it
    contributes 0 chunks until OCR'd; it currently sits in the corpus
    inert. Neither fixed yet — flagged for whoever tunes retrieval next.
  - **golden_questions.yaml rewritten against the real corpus, 2026-07-29.**
    Every expect_doc/expect_page below was cross-checked against
    `data/vitbhopal_raw/Raw Info.txt` and the 4 policy screenshots directly
    — not just against the generated PDF text — specifically to catch
    transcription drift from the PDF-generation script. It caught one real
    bug: `academic_system_ffcs.pdf`'s original clause 1.1 said a student's
    timetable choice was "subject to seat availability" — that phrase is in
    neither source; fabricated during generation. Fixed (clause reworded to
    match the source exactly) and re-ingested before writing the golden set.
    The 3 old placeholder-doc entries were retired (that doc is renamed
    `.bak` and out of the index now); replaced with 8 entries across the 5
    real docs, 1-2 per doc. The out-of-scope (WiFi) and skip
    (superseded-circular) entries are unchanged.
    **Ran `scripts/eval_retrieval.py` — real numbers, not projected:**
    recall@5 **8/8**, citation accuracy **5/8**, band match **7/8** (over
    the 8 real-doc questions; see below for why the 9th, out-of-scope,
    entry didn't complete).
    Two real findings from this run, not fixed, just reported:
    (1) **A real citation-integrity bug**, not a corpus gap: 3 of the 8
    citation misses aren't retrieval misses (recall was 8/8) — the
    rendered answer cited a marker like `[2]` or `[3]` when only 1 source
    was actually returned, printed by the eval script as `!! marker [n]
    out of range for N returned sources`. The post-processor (Non-negotiable
    #1: "every factual sentence carries a citation") strips sentences
    lacking a `[n]` marker entirely, but doesn't validate that the marker
    number is actually in range for the returned source list — an
    out-of-range marker slips through as if it were a real citation. Worth
    the next Phase 6 pass fixing directly in the post-processor, not
    per-answer.
    (2) The "hostel email contact" question (expect_band `answer`) routed
    `clarify` instead — a real band mismatch, not chased further this pass
    since confidence thresholds are explicitly still untouched.
    **The out-of-scope (WiFi) golden entry crashed the eval run**, not a
    corpus issue: its `expect_band: triage` path calls `create_ticket()`,
    which needs Postgres — Docker Desktop was not running on this machine
    at eval time (confirmed via `docker info` and `tasklist`), and starting
    it (launched, polled ~4 min) didn't bring the daemon up in time. Did
    not chase further since it's an unrelated environment gap, not a corpus
    or eval-logic defect; the 8 real-doc questions all completed and their
    numbers above are unaffected by it.
  - **Citation-integrity bug found by the above eval fixed, 2026-07-29** —
    `rag/postprocess.py`'s `enforce_citations`. Root cause was narrower and
    different from what it first looked like: it wasn't that out-of-range
    markers went unchecked (a bound check already existed); it's that
    `cited_sources` is a **compacted, re-indexed** subset of the retrieved
    sources (e.g. only source `[2]` of 5 ever gets cited -> `cited_sources`
    becomes a 1-item list), while the surviving sentence text kept the
    **original** marker number (`[2]`) unchanged — guaranteed to look
    out-of-range downstream the instant only some of the original sources
    survive. Confirmed by instrumenting the 3 failing golden questions
    directly (raw LLM answer, retrieved sources, and `enforce_citations`'s
    output) before touching any code — 2 of 3 cited a marker that was valid
    against the original 5-source list but invalid against the compacted
    one. Fixed by (1) dropping a sentence whole if *any* marker in it is
    out of range, not just when *none* are (the literal ask), and (2)
    renumbering surviving markers to match their new position in
    `cited_sources` (the actual fix for the observed symptom). Self-check:
    `tests/test_postprocess.py` (4 assertions, `python
    tests/test_postprocess.py`).
    **Re-ran the 3 previously-failing golden questions**: 2 of 3 fixed —
    "Girls Hostel building size" and "2023 highest placement package" both
    now cite correctly. The 3rd, "who do I email for hostel allocation",
    is still broken, but for an unrelated reason the fix doesn't touch: the
    LLM's raw answer that run used non-ASCII citation brackets
    (`【1】`, full-width) that `_MARKER_RE` (ASCII `\[(\d+)\]` only) never
    matches, so the whole answer gets treated as uncited ->
    `INSUFFICIENT_CONTEXT`. That's the same question already flagged with
    a band mismatch (`clarify` instead of `answer`) — left alone per this
    task's explicit instruction not to touch that question or confidence
    thresholds yet.
    **Docker Desktop was not actually installed at the path CLAUDE.md
    expected** (`C:\Program Files\Docker\Docker\Docker Desktop.exe` doesn't
    exist on this machine) — the real install is
    `C:\Users\<user>\AppData\Local\Programs\DockerDesktop\Docker
    Desktop.exe`. Found via `where docker` + a dir listing after two failed
    launch attempts at the wrong path. Started from the correct path,
    confirmed `docker info` succeeds, then `docker compose up -d postgres`
    + `pg_isready` before re-running the full eval.
    **Full eval re-run, Docker/Postgres genuinely up this time — real
    numbers, not projected:** recall@5 **8/8**, citation accuracy **7/8**
    (up from 5/8; not 8/8 — see the hostel-email caveat above), band match
    **8/9** (the out-of-scope/WiFi entry now completes end-to-end,
    `route=triage` as expected — no crash this time; the 9th entry, the
    superseded-circular question, stays `skip`ped, no doc is tagged
    superseded yet). Confidence thresholds and the hostel-email band
    mismatch still untouched, per instruction — that's the next step, not
    this one.
  - **Hostel-email band mismatch traced, 2026-07-29 — not a threshold or
    retrieval problem.** Instrumented the question directly (classify_intent
    -> retrieve -> evaluate, no code touched): `retrieval=0.785` (solid,
    correct top source), `slot_completeness=1.0`, but `answer_support=0.0`
    -> `confidence=0.614`, landing in `clarify`. Root cause: the LLM's raw
    answer for this question reliably (3/3 identical repeats) used
    full-width brackets (`【1】`) instead of ASCII `[1]`, which
    `postprocess.py`'s `_MARKER_RE` never matches, so `enforce_citations`
    strips the only sentence and the answer collapses to
    `INSUFFICIENT_CONTEXT` before confidence is even computed — the same
    citation-formatting defect flagged in the previous entry, just
    surfacing through `answer_support` instead of an out-of-range marker
    this time. A **second, independent data point emerged for free**: a
    follow-up full sweep of all 9 golden questions (to gather real
    confidence values for calibration) showed the *Girls Hostel* question
    — clean in the prior run — fail the same way this run instead. The
    failure isn't tied to one question's wording; it's a general
    intermittent LLM output-formatting lapse that can hit any question on
    any given call. Confirms this needs a genuine fix (accept more marker
    formats, or tighten the answer prompt), not a threshold change — no
    threshold value can compensate for an answer that gets stripped to
    nothing. Not fixed this pass, per instruction (still paired with the
    calibration step below, not touched separately).
  - **Phase 6 confidence-threshold calibration pass, 2026-07-29 — real
    data says leave both values where they are.** Full sweep of all 9
    executable golden questions' actual confidence values: the 7 genuine
    "answer"-band questions clustered tightly at **0.82-0.93**; the one
    genuine "triage"-band question (out-of-scope/WiFi) sat at **0.51**.
    `CONF_ANSWER_THRESHOLD=0.80` sits ~0.02 below the good cluster's floor;
    `CONF_CLARIFY_THRESHOLD=0.55` sits ~0.04 above the one real triage
    point — both already fit the real distribution with a real (if thin)
    margin on 9 data points. The only mismatch (hostel-email, 0.614) is the
    citation-formatting bug traced above, not a genuine low-confidence
    case — lowering `CONF_ANSWER_THRESHOLD` to absorb it would mask that
    bug and lower the bar for every other real production answer, which is
    the wrong trade given Non-negotiable #2. **Conclusion: no threshold
    values changed.** What *did* change: `CONF_ANSWER_THRESHOLD` /
    `CONF_CLARIFY_THRESHOLD` were defined in `.env`/`.env.example` but
    **never read anywhere in the code** — `graph/build.py`'s
    `route_after_evaluate` hardcoded `0.80`/`0.55` as literals, fully
    disconnected from those env vars. Wired them for real
    (`os.getenv(..., "0.80")` / `os.getenv(..., "0.55")` at module load, used
    in place of the literals) so a future tuning pass can actually change
    behavior by editing `.env` — confirmed a behavioral no-op via
    `py_compile` + a full eval re-run (recall@5 stayed 8/8; citation/band
    counts shifted slightly run-to-run, but that's the same LLM-formatting
    flakiness above, not this wiring — the retrieval-only recall number,
    unaffected by LLM variance, is unchanged).
  - **Both citation-formatting bugs fixed at the source, 2026-07-30** —
    `rag/postprocess.py`. (1) The full-width-bracket bug: `_MARKER_RE`
    widened to also match CJK-style `【n】` (not just ASCII `[n]`); the
    existing renumbering substitution already writes ASCII brackets back
    out, so this normalizes for free. `rag/prompts.py`'s system prompt also
    now explicitly says ASCII brackets only, with an example — a first line
    of defense, not the fix itself, since the whole point is this can't be
    trusted to hold LLM-side. (2) A **second, independently-discovered**
    bug surfaced while stress-testing the first fix: `_SENTENCE_SPLIT_RE`'s
    lookahead treated `[`/`【` as a valid "next sentence starts here"
    signal, so a marker placed right after a mid-sentence period (e.g.
    `"...sq.mt. [2] and it is a six-storey structure. [2]"`) got split into
    its own segment, tearing it away from the fact it supports — that fact
    then reads as uncited and gets dropped, degrading the answer's content
    (not just its citation) and dragging `answer_support` down enough to
    misroute to `clarify`. Fixed by dropping `[`/`【` from the lookahead
    entirely (verified nothing else relies on splitting there). Both fixes
    covered by `tests/test_postprocess.py` (6/6 assertions, 2 new
    regression cases added for these exact failure strings).
    **Full repeated 9-question sweep for both citation fixes
    (bracket-format + sentence-split) not yet completed** — blocked by
    Groq's daily 200k TPD quota, hit twice during verification (usage
    barely moved in 5 minutes between hits — a real daily cap, not a short
    burst). Current evidence: unit tests (6/6, including the two real-
    failure regression tests) and partial live spot-checks (bracket fix:
    3/3 full sweeps; sentence-split fix: proven broken via a 20-sample
    stress test showing 2/20 failures pre-fix — both the same mechanism —
    then 1/1 clean immediately post-fix before the quota cut further
    testing off). Re-run the full sweep 2-3x once quota resets (check
    timing) or before final demo rehearsal, whichever comes first — **do
    not skip this before the actual demo.**
  - **Corpus expanded to cover `od_leave_request`, `attendance_query`, and
    `fee_scholarship` — previously zero-coverage intents — 2026-07-30.**
    Three new authored docs: `od_leave_policy.pdf`, `attendance_policy.pdf`,
    `fee_scholarship.pdf` (same plain-text/`Chapter N — Title` structure as
    the other authored docs). Content was cross-checked directly against
    `data/vitbhopal_raw/Raw Info.txt`'s new paragraph, not invented. Two real
    ambiguities surfaced in that raw text and were **not** guessed past —
    written into the PDFs themselves as open/unconfirmed, per explicit
    instruction: (1) the "5 ODs" cap has no stated renewal period in the raw
    source (per-semester / per-year / total-across-degree are all equally
    plausible reads) — `od_leave_policy.pdf` clause 1.3 states the cap and
    says the renewal period isn't confirmed, rather than picking one; (2) the
    raw text describes an old attendance sliding-marks scale then says "it
    have been update now" without ever stating the new scheme — the 75%
    exam-eligibility threshold is stated as confirmed (clause 1.1), but the
    old marks-by-attendance-band scale is written as "found in older
    material, current status unconfirmed" (clause 1.2), not asserted as
    still-active or fully superseded. No `golden_questions.yaml` entry asks
    the exact "how many ODs before X" question for the same reason.
    Re-ingested full corpus (wiped `services/api/qdrant_data/` first): **23
    chunks** total (was 19) — all 4 new chunks landed with real `Chapter N —
    Title` section labels, zero `General` defaulting, confirmed via direct
    Qdrant payload scroll. `search()`-level recall checked directly (not
    through the full LLM/citation path, to avoid burning Groq's daily quota
    again per the note above) for all 4 new golden questions — all 4 hit
    their expected doc/page in the top-5. Full end-to-end eval (citation
    accuracy, confidence band) against the new entries not yet run — same
    Groq-quota constraint, same "before final demo" caveat as above applies
    to these too now.
    **Also found and fixed while doing this pass:** the same `data/`
    directories had accumulated real-world clutter that isn't corpus
    material at all — six blank admission/legal forms (ragging affidavit,
    day-boarder application, two hostel-vacating consent forms, an
    undertaking form, a DPDPA consent form; one of them explicitly for "VIT,
    Vellore," the wrong campus) moved out of `data/seed_pdfs/` into
    `data/reference_only/` so it's unambiguous at a glance they're not part
    of the ingested corpus, and one file that was never campus material to
    begin with — a personal IndiGo flight e-ticket (PNR, seat, masked card
    digits) — deleted outright rather than just excluded.
  - **Full 14-question eval run, 2026-07-30/31 — Docker/Postgres/Qdrant
    genuinely up, real numbers.** recall@5 **12/12**, citation accuracy
    **11/12**, band match **12/13** (13 executable; the 14th, superseded-
    circular, still `skip`ped, no doc tagged superseded yet). 3 of the 4
    new `od_leave_request`/`attendance_query`/`fee_scholarship` questions
    passed cleanly; the OD-leave "which email" question is the sole
    failure across the whole run (both the citation and band misses trace
    to it).
    **Traced that failure — not a citation-formatting bug.** Suspected at
    first it might be a recurrence of the full-width-bracket or
    sentence-split bugs fixed 2026-07-30 (see above); it isn't. Captured
    the raw LLM answer directly (bypassing the graph) 3x: clean ASCII
    `[1]` every time, correct single citation, nothing for
    `enforce_citations` to strip. Ran the **full graph** 3x instead:
    identical result all 3 runs (deterministic, not intermittent) —
    `route=clarify`, `reason_codes=['MISSING_SLOT']`, answer is the
    slot-prompt template ("Could you provide... event_date?"), which
    carries zero citation markers. Root cause is the intent-design gap
    documented above under "What NOT to do": `classify_intent` correctly
    tags the question `od_leave_request`, but `REQUIRED_SLOTS` demands
    `event_date`/`event_reason` even for a policy lookup, and
    `route_after_evaluate` checks `missing_slots` before confidence — so
    the question never reaches a cited answer at all. Not fixed this
    pass, per instruction.
  - **Escalation-chain content added to `od_leave_policy.pdf` and
    `hostel_facilities.pdf`, 2026-07-31.** `od_leave_policy.pdf` +Chapter 2
    (Escalation Path: unresolved issue -> Program Chair (PC) ->
    Controller of Examinations (COE) -> Dean of Academics, final
    authority; PC contacts for branches other than BCE explicitly named
    as unconfirmed). `hostel_facilities.pdf` +Chapter 4 (Hostel Grievance
    Escalation: minor issues, e.g. room changes, -> Warden; serious/
    unresolved -> Chief Warden) and +Chapter 5 (Hostel Conduct Rules:
    parents not permitted inside hostel premises with a fine, amount
    unconfirmed; a separate PDA fine exists, hostel-specific-vs-campus-
    wide scope unconfirmed). **Unlike the rest of this corpus, this
    content was not cross-checked against `data/vitbhopal_raw/`** — the
    escalation chain and Warden/Chief-Warden split aren't present
    anywhere in the scraped raw material (`Raw Info.txt` or the 5
    screenshots/webp); authored directly per explicit instruction, on the
    same trust basis as the already-documented `pc.bce@vitbhopal.ac.in`
    contact, not derived from the crawled source. The fine amounts and
    the PDA rule's scope genuinely are open gaps per the raw material and
    are written into the PDF as unconfirmed, same treatment as the OD-cap
    renewal period and the attendance marks-scale gap above.
    Re-ingested full corpus (wiped `services/api/qdrant_data/` first):
    **26 chunks** total (was 23) — `od_leave_policy.pdf` 1->2 chunks,
    `hostel_facilities.pdf` 3->5 chunks. Section-label smoke test: both
    new pages landed real `Chapter N -- Title` labels, zero `General`
    defaulting (the 8 pre-existing `General` chunks are all the
    tabular curriculum PDF, unrelated known gap). `search()`-level recall
    checked directly for both new fact areas (not the full LLM path, to
    avoid burning Groq's daily quota) — both hit their expected doc/page
    at rank 1. 2 new `golden_questions.yaml` entries added, for the
    escalation chain and the Warden/Chief-Warden split only — no entry
    for the fine amounts or the PDA scope, per the same unconfirmed-gap
    policy. Full end-to-end eval (citation accuracy, confidence band)
    against these 2 new entries not yet run.