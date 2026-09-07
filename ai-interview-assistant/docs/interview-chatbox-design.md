# AI Interview Assistant — Interview Chatbox (Phase 1 Design)

> Status: **Design / proposal**. This document defines the UI idea and the API list for the
> multi-turn interview chatbox. No implementation yet — this is the spec to build against.

---

## 1. Concept — Workshop 2: Mock Interview Chatbot

This is **Workshop 2** of the AI Interview Copilot roadmap (W1 → W5). Workshop 1 produced an
**Interview Question Generator**: given role / level / skills / count, it generates a question set
(prompt + logic in `Backend/app/prompts/`). Workshop 2 **reuses that question set** and turns it into a
**live, multi-turn mock interview**.

The role flips: instead of generating (or answering) questions in one shot, the AI now **conducts**
the interview.

| | W1 — Question Generator | W2 — Mock Interview Chatbot |
|---|---|---|
| Interaction | Single-shot generate | **Multi-turn conversation** |
| Who drives | User reads output | **AI asks, user answers — one Q at a time** |
| Adapts? | No | **Yes — next question / follow-up depends on the answer** |
| Memory | Stateless | **Context management across turns** |
| Output | Question list (+ answer hints) | **Saved transcript + end-of-interview feedback** |

Two capabilities called out for W2, both implemented with **function calling**:

1. **Save interview history** → a `save_history` service function, invoked every turn.
2. **End-of-interview summary** → a dedicated LLM call using a forced tool (`submit_evaluation`)
   that returns structured, parseable **practice feedback**.

> **Framing (matches the roadmap):** the summary is **coaching feedback to help the candidate
> practise** — strengths, gaps, and how to improve. It is **not** an automated hire / no-hire
> verdict. Per the project's own principle, AI only synthesises and compares against the JD;
> **the hiring decision stays with a human.**

---

## 2. UX / UI design

### 2.1 Screen states (one screen, four states)

```
SETUP ──Start──▶ IN_PROGRESS ──End──▶ ENDED ──evaluate──▶ SUMMARIZED
```

- **SETUP** — header form is expanded; sidebar/chat empty.
- **IN_PROGRESS** — header collapses to a compact chip bar; chat + sidebar active.
- **ENDED** — input disabled; "Evaluating…" indicator; Summary button becomes primary.
- **SUMMARIZED** — Summary panel/modal shown with scores and feedback.

### 2.2 Layout (matches your sketch, refined)

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER (Setup)  Job Role | Level ▼ | Skills (tags) | JD ▾ | [Start] │
│  after start →  «Senior Backend · Python, FastAPI, PostgreSQL» [Edit]│
├───────────────┬────────────────────────────────────────────────────┤
│  SIDEBAR      │  CHAT                                               │
│  Progress 3/8 │  ┌ Bot  Q3: How would you design rate limiting?  │
│  ▓▓▓░░░░░      │  └ ...                                             │
│  Q1 ✅ 4/5    │  ┌ You  I'd use a token-bucket per API key…       │
│  Q2 ✅ 3/5    │  └ ...                                             │
│  Q3 🔄 (now)  │  ┌ Bot  Follow-up: how do you store the counters? │
│  Q4 ⚪         │  └ ...                                             │
│  …            │  [ type your answer…            ] [Skip] [Send ▶] │
├───────────────┴────────────────────────────────────────────────────┤
│ FOOTER   [ End Interview ]                     [ View Summary ]     │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 Component breakdown

**Header / Setup bar**
- Fields: **Job Role** (text), **Level** (select: Intern/Fresher/Junior/Mid/Senior/Lead),
  **Skills** (tag input), **Job Description / project info** (collapsible textarea, optional).
- Options: **# questions** (default 6), **Language** (VI/EN), **Style** (Technical / Behavioral / Mixed).
- Primary button **Start Interview** → `POST /api/interviews`.
- After start: collapses to a summary chip row with an **Edit** affordance (editing restarts session).

**Sidebar / Progress**
- Overall progress `answered / total` + progress bar.
- Question list; each row shows status icon and (once graded) a mini score:
  - ✅ answered · 🔄 current · ⚪ upcoming · ⏭️ skipped
- Clicking a row scrolls the chat to that Q/A (read-only navigation).

**Chat box (main)**
- Message bubbles: **bot** left, **user** right; system/tool events hidden or shown as subtle dividers.
- Bot bubbles carry questions, follow-ups, and short acknowledgements.
- **Typing indicator** while the model is thinking; optional **token streaming**.
- Input: multiline textarea, **Enter** = send, **Shift+Enter** = newline.
- Inline controls: **Send**, **Skip question**, (optional) **Ask for clarification**.

**Footer / Actions**
- **End Interview** (primary once ≥1 answer) → `POST /api/interviews/{id}/end`.
- **View Summary** (enabled after end) → opens Summary.
- (optional) **Export transcript** (Markdown / JSON).

**Summary view (modal or right panel)**
- Overall score + hire recommendation.
- Competency breakdown (bars or radar): e.g. Technical depth, Communication, Problem-solving.
- Strengths / Areas to improve (bullets).
- Per-question feedback with scores.
- Actions: Copy, Export (MD/JSON/PDF later), Start new interview.

### 2.4 Cross-cutting UI states
- Loading (start, per-answer, evaluating), empty (no session), error + retry, reconnect/resume
  (rehydrate from `GET /api/interviews/{id}`).

---

## 3. Data model

```
InterviewSession
  id: str (uuid)
  status: "created" | "in_progress" | "ended" | "summarized"
  config: InterviewConfig
  questions: Question[]
  messages: Message[]
  current_question_index: int
  summary: Summary | null
  created_at, updated_at: datetime

InterviewConfig
  job_role: str
  level: "intern"|"fresher"|"junior"|"mid"|"senior"|"lead"
  skills: str[]
  job_description: str | null
  num_questions: int = 6
  language: "vi" | "en" = "vi"
  style: "technical" | "behavioral" | "mixed" = "mixed"

Question
  id: str
  index: int
  text: str
  skill_tag: str | null
  type: "technical"|"behavioral"|"system_design"|"coding"|"hr"
  status: "pending"|"current"|"answered"|"skipped"
  score: int | null        # 0..5, filled progressively or at evaluation
  follow_up_count: int

Message
  id: str
  role: "system" | "assistant" | "user" | "tool"
  content: str
  question_id: str | null
  created_at: datetime

Summary
  overall_score: int          # 0..100  (practice score — NOT a hiring verdict)
  readiness: "needs_practice" | "getting_there" | "interview_ready"
  competencies: { name: str, score: int, comment: str }[]   # score 0..5
  strengths: str[]
  improvements: str[]
  per_question: { question_id: str, score: int, feedback: str }[]
  summary_text: str
```

**Storage (Phase 1):** in-memory dict + optional JSON snapshot per session under `data/`.
Swap for SQLite/Postgres in Phase 2 behind a `SessionStore` interface.

---

## 4. API list

Base prefix `/api`. All bodies/responses JSON. `{id}` = session id.

| # | Method & path | Purpose | UI trigger |
|---|---|---|---|
| 1 | `POST /api/interviews` | Create session from config, generate question plan, return session + first question | Header **Start Interview** |
| 2 | `GET /api/interviews/{id}` | Full session state (resume / reload) | Page load / reconnect |
| 3 | `GET /api/interviews` | List sessions (history) — *optional P1* | History view |
| 4 | `DELETE /api/interviews/{id}` | Delete a session — *optional* | History view |
| 5 | `POST /api/interviews/{id}/answer` | **Core loop.** Submit answer → AI returns next bot message(s) + progress + whether it advanced | Chat **Send** |
| 6 | `POST /api/interviews/{id}/answer/stream` | SSE streaming variant of #5 — *optional* | Chat **Send** (streamed) |
| 7 | `POST /api/interviews/{id}/skip` | Skip current question, advance — *optional* | **Skip** button |
| 8 | `GET /api/interviews/{id}/questions` | Question list + statuses + scores | Sidebar render |
| 9 | `GET /api/interviews/{id}/messages` | Full transcript | Chat rehydrate / export |
| 10 | `POST /api/interviews/{id}/end` | End interview; run evaluation; return (or start) summary | Footer **End Interview** |
| 11 | `GET /api/interviews/{id}/summary` | Fetch evaluation summary | Footer **View Summary** |
| 12 | `POST /api/interviews/{id}/summary?regenerate=true` | Re-run evaluation — *optional* | Summary "Regenerate" |
| 13 | `GET /api/health` | Health check | infra |
| 14 | `GET /api/meta/options` | Enum options for dropdowns (levels/styles/languages) — *optional* | Setup form |

**Core Phase-1 set = 1, 2, 5, 8, 9, 10, 11** (+ 13 health). The rest are optional niceties.

### 4.1 Key request/response shapes

**#1 Create** — `POST /api/interviews`
```jsonc
// request
{ "job_role": "Backend Engineer", "level": "senior",
  "skills": ["Python","FastAPI","PostgreSQL"],
  "job_description": "…", "num_questions": 6, "language": "vi", "style": "mixed" }
// response
{ "session_id": "…", "status": "in_progress",
  "questions": [{ "id": "q1", "index": 0, "text": "…", "status": "current" }, …],
  "first_message": { "role": "assistant", "content": "Xin chào! Câu hỏi 1: …" },
  "progress": { "answered": 0, "total": 6 } }
```

**#5 Answer** — `POST /api/interviews/{id}/answer`
```jsonc
// request
{ "message": "I'd use a token-bucket per API key…", "question_id": "q3" }
// response
{ "messages": [{ "role": "assistant", "content": "Nice — follow-up: …" }],
  "action": "follow_up",            // "follow_up" | "next_question" | "end_interview"
  "current_question": { "id": "q3", "index": 2, "status": "current" },
  "progress": { "answered": 2, "total": 6 },
  "done": false }
```

**#10 End** — `POST /api/interviews/{id}/end` → returns `Summary` (or `202` + poll `#11`).

---

## 5. Multi-turn conversation flow

```
Start:  config ─▶ LLM: generate question plan (structured) ─▶ store ─▶ send Q1

Loop (per answer):
  user answer
     └▶ append to messages (save_history)
     └▶ LLM(interviewer): system + config + plan + running transcript + TOOL
            └▶ returns decision via `interviewer_turn` tool:
                 { reply, action, current_question_eval? }
     └▶ server applies action:
            follow_up      → send reply, stay on same question
            next_question  → grade current, advance index, append next question to reply
            end_interview  → go to End
     └▶ save_history()

End:
  LLM(evaluator) over full transcript with forced `submit_evaluation` tool
     └▶ structured Summary ─▶ store ─▶ status = summarized ─▶ UI shows Summary
```

Stop conditions: all questions answered, user clicks **End**, or model chooses `end_interview`.

### 5.1 Context management (core W2 addition)

A multi-turn interview grows the transcript every turn, so we can't naively resend everything. Each
`/answer` call rebuilds the model context from bounded parts:

```
[ system: interviewer persona ]
[ config: role / level / skills / language / style ]
[ the full question plan (short) + which question is current ]
[ rolling_summary: 1-2 lines summarising older answered questions ]   ← compresses the tail
[ recent turns verbatim: last N messages of the current question ]     ← keeps local detail
[ the candidate's newest answer ]
```

- **Recent window** kept verbatim (last N turns) for local coherence in follow-ups.
- **Older turns** collapsed into `rolling_summary` (per-question one-liners) so token cost stays flat
  as the interview grows. Reuse `Backend/app/utils/token_utils.py` (`estimate_tokens`,
  `truncate_to_token_budget`) to enforce a budget; upgrade to a real tokenizer later.
- Per-question scores captured during the interview also feed the final evaluation, so the evaluator
  doesn't have to re-read the entire raw transcript.

---

## 6. Function-calling design (the two "function calls")

### 6.1 `interviewer_turn` — reliable turn control (during `/answer`)
Force the model to return a decision as a tool call so the server always knows what to do:
```jsonc
{
  "name": "interviewer_turn",
  "parameters": {
    "reply": "string — what to say to the candidate",
    "action": "follow_up | next_question | end_interview",
    "current_question_eval": { "score": "0-5", "note": "string" }  // optional, progressive grading
  }
}
```

### 6.2 `save_history` — persist the transcript ("lưu chat history")
Implemented as a **service function** called automatically every turn (recommended — simplest and
reliable). It appends the user message, the bot reply, and any progressive score to the store.
> You *can* expose it as an LLM tool if you want the model to control persistence, but that adds
> failure modes without benefit — keep saving deterministic on the server.

### 6.3 `submit_evaluation` — LLM evaluation at the end ("function call LLM để đánh giá")
A separate LLM call over the whole transcript with `tool_choice` forced to this tool, guaranteeing
structured output:
```jsonc
{
  "name": "submit_evaluation",
  "parameters": {
    "overall_score": "0-100 (practice score)",
    "readiness": "needs_practice|getting_there|interview_ready",
    "competencies": [{ "name": "Technical depth", "score": "0-5", "comment": "…" }],
    "strengths": ["…"],
    "improvements": ["…"],
    "per_question": [{ "question_id": "q1", "score": "0-5", "feedback": "…" }],
    "summary_text": "…"
  }
}
```
> Keep it coaching-oriented: the output helps the candidate improve. Final hiring calls are human.

---

## 7. Prompts to add (`Backend/app/prompts/`)
- `interviewer_system_prompt.txt` — persona: *you are the interviewer*; ask one question at a time;
  adapt to answers; stay concise; honour role/level/skills/language.
- `question_plan_prompt.txt` — **reuse Workshop 1's generator prompt/logic** to turn config into N
  ordered questions (JSON list). This is the W1 → W2 handoff.
- `evaluation_prompt.txt` — from transcript → structured evaluation via `submit_evaluation`.

The existing `system_prompt.txt` / `interview_prompt.txt` describe the *old* answer-helper role and
should be retired or kept only for a separate "quick ask" mode.

---

## 8. Backend module plan (fits current structure)
```
Backend/app/
  api/interview_router.py        # endpoints in §4  (keep chat_router.py for legacy /chat or remove)
  services/interview_service.py  # turn orchestration, calls tools, applies actions
  services/evaluation_service.py # end-of-interview evaluation (submit_evaluation)
  services/question_service.py   # generate question plan from config
  stores/session_store.py        # SessionStore interface + InMemory/JSON impl
  models/interview.py            # Pydantic models in §3
  prompts/interviewer_system_prompt.txt, question_plan_prompt.txt, evaluation_prompt.txt
```
Reuse `clients/openai_client.py`, `config/settings.py`, `utils/`.

---

## 9. Roadmap fit (W1 → W5)
- **W1 — Question Generator (done):** generate a question set from role/level/skills. W2 reuses it as
  the question-plan step.
- **W2 — Mock Interview Chatbot (this doc):** multi-turn interview, context management, save history,
  end-of-interview feedback, summary view. Store = in-memory + JSON snapshot.
- **W3 — Voice Interview Simulator:** add STT/TTS around the same turn loop; `/answer` gains an audio
  variant. Same session model.
- **W4 — Technical Interview RAG Bot:** ground questions and feedback in a knowledge base; add a
  retrieval step before question generation and evaluation.
- **W5 — Enterprise Recruitment Copilot:** JD matching, multi-user/auth, DB persistence, analytics.
  AI synthesises and compares to the JD; **humans make the hiring decision.**

## 10. Open decisions (need your call before implementation)
1. **Persistence:** in-memory + JSON file (fast to build) **vs** SQLite (survives restart)?
2. **Frontend:** should I scaffold a minimal one (plain HTML/JS served by FastAPI, or React), or
   keep this backend-only and you build the UI separately?
3. **Progressive grading:** grade each answer as we go (shows scores in sidebar live) **vs** grade
   everything only at the end (cheaper, one LLM call)?
4. **Legacy `/api/chat`:** keep as a separate "quick ask" mode, or remove?
