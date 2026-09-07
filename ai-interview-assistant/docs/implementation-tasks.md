# Implementation Task List — W2 Mock Interview Chatbot (BE + FE)

> Work breakdown for building the multi-turn mock interview. Based on
> [interview-chatbox-design.md](interview-chatbox-design.md) (UI, API, data model) and
> [interview-workflow.md](interview-workflow.md) (runtime flow).

**Legend:** `[ ]` todo · **MVP** = needed for a working end-to-end demo · **Later** = polish / optional.
IDs (`BE-1`, `FE-2`) are for cross-reference in PRs and standups.

---

## 0. Shared / cross-cutting

- [ ] **SH-1** Agree the **API contract** (endpoints + request/response shapes) from design doc §4 before FE/BE split — **MVP**
- [ ] **SH-2** Decide **persistence**: in-memory + JSON file vs SQLite (design doc §10) — **MVP**
- [ ] **SH-3** Decide **FE stack**: plain HTML/JS served by FastAPI vs React (Vite) — **MVP**
- [ ] **SH-4** Enable **CORS** on the API for the FE origin — **MVP**
- [ ] **SH-5** Keep FE/BE in sync via the generated **OpenAPI schema** (`/docs`, `/openapi.json`) — Later

---

## 1. Backend (BE)

### BE-A · Scaffolding
- [ ] **BE-A1** Create module structure (design doc §8): `app/api/interview_router.py`,
  `app/services/{interview_service,question_service,evaluation_service}.py`,
  `app/stores/session_store.py`, `app/models/interview.py`, new prompt files — **MVP**
- [ ] **BE-A2** Register `interview_router` in `main.py`; decide keep/remove legacy `chat_router` — **MVP**
- [ ] **BE-A3** Extend `app/config/settings.py` + `.env.example` (model names, default #questions,
  follow-up cap, CORS origins, storage path) — **MVP**

### BE-B · Data models (Pydantic) → `app/models/interview.py`
- [ ] **BE-B1** Core models: `InterviewConfig`, `Question`, `Message`, `InterviewSession`,
  `Competency`, `Summary` (design doc §3) — **MVP**
- [ ] **BE-B2** Enums: `Level`, `Style`, `Language`, `SessionStatus`, `QuestionStatus`,
  `TurnAction`, `Readiness` — **MVP**
- [ ] **BE-B3** Request/response models: `CreateInterviewRequest/Response`, `AnswerRequest/Response`,
  `QuestionsResponse`, `SummaryResponse` — **MVP**

### BE-C · Session store → `app/stores/session_store.py`
- [ ] **BE-C1** `SessionStore` interface (`create`, `get`, `list`, `append_message`, `update`) — **MVP**
- [ ] **BE-C2** `InMemorySessionStore` implementation — **MVP**
- [ ] **BE-C3** `save_history()` — append user/bot turns, update question status + scores (workflow §7) — **MVP**
- [ ] **BE-C4** JSON snapshot persistence per session under `data/` (load on startup) — **MVP** *(or SQLite per SH-2)*

### BE-D · Prompts → `app/prompts/`
- [ ] **BE-D1** `interviewer_system_prompt.txt` — interviewer persona; one question at a time; adapt;
  concise; honour role/level/skills/language (workflow §4.1) — **MVP**
- [ ] **BE-D2** `question_plan_prompt.txt` — **reuse W1 generator** → N ordered questions as JSON — **MVP**
- [ ] **BE-D3** `evaluation_prompt.txt` — transcript + scores → structured feedback — **MVP**
- [ ] **BE-D4** Retire or repurpose legacy `system_prompt.txt` / `interview_prompt.txt` — Later

### BE-E · OpenAI client — tool/function calling
- [ ] **BE-E1** Add **tool-calling** support (the current `chat_service` only does plain
  completions); helper to call with a forced tool and parse the tool-call arguments — **MVP**
- [ ] **BE-E2** Robust parse/validate of tool args into Pydantic (retry/repair on malformed JSON —
  a known W1 issue) — **MVP**
- [ ] **BE-E3** Error handling: API key, rate limit, timeout, empty response → typed errors — **MVP**

### BE-F · Question plan → `app/services/question_service.py`
- [ ] **BE-F1** `generate_plan(config)` → ordered `Question[]` (reuses BE-D2) — **MVP**
- [ ] **BE-F2** Validate count/shape; enforce required config; fallback if the model under-delivers — **MVP**

### BE-G · Interview turn (core loop) → `app/services/interview_service.py`
- [ ] **BE-G1** `start(config)` → create session, generate plan, compose + save opening message (Phase A) — **MVP**
- [ ] **BE-G2** `answer(session_id, message)` — save user turn → assemble context → call
  `interviewer_turn` (forced) → parse decision (workflow §4) — **MVP**
- [ ] **BE-G3** Apply `action`: `follow_up` / `next_question` (grade + advance) / `end_interview` — **MVP**
- [ ] **BE-G4** Follow-up **cap** (e.g. max 2) → force `next_question` when exceeded — **MVP**
- [ ] **BE-G5** Store progressive `current_question_eval` (score + note) on the question — **MVP**
- [ ] **BE-G6** `skip(session_id)` — mark skipped, advance, no LLM call — Later

### BE-H · Context management (workflow §6)
- [ ] **BE-H1** Assemble bounded context: persona + config + compact plan + `rolling_summary` +
  last-N verbatim + new answer — **MVP**
- [ ] **BE-H2** Update `rolling_summary` when a question closes — **MVP**
- [ ] **BE-H3** Enforce a token budget using `app/utils/token_utils.py` — Later

### BE-I · Evaluation (Phase C) → `app/services/evaluation_service.py`
- [ ] **BE-I1** `evaluate(session)` — transcript + per-question scores → `submit_evaluation`
  (forced) → `Summary` (workflow §5) — **MVP**
- [ ] **BE-I2** Persist summary; set `status = summarized`; make idempotent (`?regenerate=true`) — **MVP**
- [ ] **BE-I3** Keep output coaching-oriented (`readiness`, not a hire verdict) — **MVP**

### BE-J · API endpoints → `app/api/interview_router.py`
- [ ] **BE-J1** `POST /api/interviews` → start (BE-G1) — **MVP**
- [ ] **BE-J2** `GET /api/interviews/{id}` → full state (resume) — **MVP**
- [ ] **BE-J3** `POST /api/interviews/{id}/answer` → turn loop (BE-G2) — **MVP**
- [ ] **BE-J4** `GET /api/interviews/{id}/questions` → sidebar data — **MVP**
- [ ] **BE-J5** `GET /api/interviews/{id}/messages` → transcript — **MVP**
- [ ] **BE-J6** `POST /api/interviews/{id}/end` → evaluate (BE-I1) — **MVP**
- [ ] **BE-J7** `GET /api/interviews/{id}/summary` → feedback — **MVP**
- [ ] **BE-J8** `GET /api/health` — **MVP**
- [ ] **BE-J9** Optional: `/skip`, `GET /api/interviews`, `/answer/stream` (SSE), `GET /api/meta/options` — Later

### BE-K · Validation, errors, safety
- [ ] **BE-K1** Validate required config; reject empty/oversized input — **MVP**
- [ ] **BE-K2** `404` unknown session; `409` wrong state (e.g. answering an ended interview) — **MVP**
- [ ] **BE-K3** Guard prompt-injection in answers (answers are data, not instructions) — Later

### BE-L · Tests → `tests/`
- [ ] **BE-L1** **Fix existing mismatch**: `tests/test_chat_service.py` calls `chat()` with 2 args
  but the impl takes 1 — reconcile signature or update the test — **MVP**
- [ ] **BE-L2** Unit: session store + `save_history` — **MVP**
- [ ] **BE-L3** Unit: turn decision apply-logic with a mocked LLM (follow_up / next / end, cap) — **MVP**
- [ ] **BE-L4** Unit: question-plan parsing + evaluation parsing (mocked tool calls) — **MVP**
- [ ] **BE-L5** Test matrix across roles / levels / skills (carry over W1 test cases) — Later

### BE-M · Docs / DX
- [ ] **BE-M1** Update `README.md`: new endpoints + run steps; link the design/workflow docs — **MVP**
- [ ] **BE-M2** Swagger tags + summaries on each route — Later

---

## 2. Frontend (FE)

### FE-A · Setup
- [ ] **FE-A1** Scaffold per SH-3 (static page served by FastAPI, or React/Vite) — **MVP**
- [ ] **FE-A2** `api` client module — typed fetch wrappers for every endpoint; base URL from env — **MVP**
- [ ] **FE-A3** Global styles / theme (light + dark), layout tokens — **MVP**

### FE-B · Layout shell (mockup)
- [ ] **FE-B1** Four-region layout: Header / Sidebar / Chat / Footer — **MVP**
- [ ] **FE-B2** Responsive behaviour + empty state (no session) — Later

### FE-C · Setup form (Header)
- [ ] **FE-C1** Fields: role, level (select), skills (tag input), JD (textarea), #questions,
  language, style — **MVP**
- [ ] **FE-C2** Client-side validation (required fields) — **MVP**
- [ ] **FE-C3** **Start interview** → `POST /interviews`; render Q1; move to in-progress — **MVP**
- [ ] **FE-C4** Collapse to chip bar after start + **Edit setup** (restart) — Later

### FE-D · Chat box
- [ ] **FE-D1** Message bubbles (bot left / user right), role labels — **MVP**
- [ ] **FE-D2** Input: textarea, **Enter** = send / **Shift+Enter** = newline; **Send** button — **MVP**
- [ ] **FE-D3** Submit answer → `POST /answer`; append reply; handle `follow_up` vs `next_question` — **MVP**
- [ ] **FE-D4** Typing / loading indicator while awaiting the model — **MVP**
- [ ] **FE-D5** Auto-scroll; disable input while pending / after end — **MVP**
- [ ] **FE-D6** **Skip** control → `/skip` (if BE-G6 shipped) — Later
- [ ] **FE-D7** Token **streaming** via SSE (if BE-J9 shipped) — Later

### FE-E · Sidebar / progress
- [ ] **FE-E1** Progress bar (`answered / total`) — **MVP**
- [ ] **FE-E2** Question list with status icons (answered / current / upcoming / skipped) — **MVP**
- [ ] **FE-E3** Live update after each turn (from `/answer` response) — **MVP**
- [ ] **FE-E4** Per-question mini score + click-to-scroll to that Q/A — Later

### FE-F · Footer actions
- [ ] **FE-F1** **End interview** → `POST /end` (with confirm) — **MVP**
- [ ] **FE-F2** **View summary** (enabled after end) — **MVP**
- [ ] **FE-F3** Export transcript (Markdown / JSON) — Later

### FE-G · Summary view
- [ ] **FE-G1** Panel/modal: overall score + `readiness` badge — **MVP**
- [ ] **FE-G2** Competency bars, strengths, improvements, per-question feedback — **MVP**
- [ ] **FE-G3** "Feedback to help you practise — not a hiring decision" note — **MVP**
- [ ] **FE-G4** Copy / export / start-new-interview — Later

### FE-H · State & resume
- [ ] **FE-H1** Store `session_id` (localStorage); rehydrate via `GET /interviews/{id}` on reload — **MVP**
- [ ] **FE-H2** Drive UI from `status` (created / in_progress / ended / summarized) — **MVP**

### FE-I · UX states & a11y
- [ ] **FE-I1** Loading / error + retry / reconnect handling with clear messages — **MVP**
- [ ] **FE-I2** Keyboard nav, ARIA labels, focus management, sentence-case copy — Later

### FE-J · QA
- [ ] **FE-J1** Manual E2E happy path (start → answer several → end → summary) — **MVP**
- [ ] **FE-J2** Edge cases: skip, end early, refresh mid-interview, API error — Later

---

## 3. Suggested milestones (sequence)

1. **M1 — Contract & scaffold:** SH-1..4, BE-A*, BE-B*, FE-A* → agreed API + empty app runs.
2. **M2 — Start + first question:** BE-C*, BE-D1/D2, BE-E1/E2, BE-F*, BE-G1, BE-J1/J2/J8 + FE-B*, FE-C* →
   you can start an interview and see Q1.
3. **M3 — The loop:** BE-G2..G5, BE-H1/H2, BE-J3/J4/J5 + FE-D*, FE-E1..E3, FE-H* →
   full multi-turn conversation with adaptive follow-ups + live progress.
4. **M4 — Evaluation:** BE-D3, BE-I*, BE-J6/J7 + FE-F1/F2, FE-G1..G3 →
   end interview → coaching feedback. **← end-to-end MVP demo.**
5. **M5 — Hardening & polish:** BE-K*, BE-L*, BE-M* + FE-D6/D7, FE-E4, FE-F3, FE-G4, FE-I* + Later items.

## 4. Dependency notes
- FE work needs the **API contract** (SH-1) locked; FE can then mock responses until BE endpoints land.
- **BE-E1 (tool calling)** unblocks BE-G2 and BE-I1 — build it early; the current `chat_service`
  path does plain completions only.
- **SH-2 (persistence)** affects BE-C4 only; the rest of BE is storage-agnostic behind `SessionStore`.
