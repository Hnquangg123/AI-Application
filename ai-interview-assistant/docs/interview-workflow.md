# AI Interview Assistant — Mock Interview Workflow (Workshop 2)

> Companion to [interview-chatbox-design.md](interview-chatbox-design.md). That doc defines the UI,
> API list, and data model. **This doc explains the runtime workflow** — how a multi-turn mock
> interview actually flows, turn by turn, from setup to the final feedback summary.

---

## 1. What this covers

Workshop 2 turns the Workshop 1 **question generator** into a **live, multi-turn mock interview**:
the AI asks one question at a time, adapts the next message to the candidate's answer, saves every
turn, and produces coaching feedback at the end.

The run has **three phases**:

```
PHASE A                 PHASE B                              PHASE C
Start  ───────────▶  Turn loop (repeats per answer)  ───────────▶  End & evaluate
generate plan        ask · answer · adapt · save                   score → feedback
send Q1                                                            summary shown
```

---

## 2. Components involved

| Component | Role |
|---|---|
| Client (chat UI) | Renders questions, sends answers, shows progress + summary |
| `interview_router` | HTTP endpoints (see design doc §4) |
| `interview_service` | Orchestrates a turn: context → model → apply action → persist |
| `question_service` | Generates the question plan (reuses Workshop 1) |
| `evaluation_service` | End-of-interview scoring (Phase C) |
| `session_store` | Persistence — `save_history()` / load |
| LLM · `interviewer_turn` tool | Decides follow-up vs next vs end each turn |
| LLM · `submit_evaluation` tool | Produces the structured feedback (once, at the end) |

---

## 3. Phase A — Start (runs once)

Triggered by **Start interview** → `POST /api/interviews` with the config
(role, level, skills, JD, #questions, language, style).

1. **Generate the question plan** — one-shot LLM call that **reuses Workshop 1's generator prompt**
   to turn the config into an ordered list of questions. Stored with `q0 = current`, the rest
   `pending`.
2. **Send Question 1** — the server composes the opening bot message (greeting + Q1), saves it with
   `save_history()`, and returns it. The UI renders Q1.

No back-and-forth conversation has happened yet — this phase only builds the plan and asks the first
question.

---

## 4. Phase B — The turn loop (repeats every answer)

This is the core of Workshop 2. Every answer the candidate sends to
`POST /api/interviews/{id}/answer` runs one full cycle:

```
            ┌─────────────────────────────────────────────┐
            ▼                                               │  loop per answer
  1. Candidate submits answer   (POST …/answer)             │
            │                                               │
  2. Save answer to history     save_history()   ★          │
            │                                               │
  3. Assemble context   persona · plan · summary · recent   │
            │                                               │
  4. Ask the model      interviewer_turn tool    ★          │
            │                                               │
  5. Decision: action? ───────────┬───────────────┐        │
            │                      │               │        │
       follow_up            next_question     end_interview │
     (probe same Q)       (grade · advance)     (wrap up)   │
            │                      │               │        │
            └───────────┬──────────┘               ▼        │
                        │                    PHASE C         │
  6. Save turn · update progress   save_history()  ★         │
                        │                                    │
  7. Return to UI  (next question / follow-up)  ─────────────┘

  ★ = function call
```

### Step by step

1. **Receive** the answer (with the `question_id` it belongs to).
2. **Save the user turn first** with `save_history()` — *before* the model call, so nothing is lost
   if the LLM call fails and the turn can be retried.
3. **Assemble bounded context** (see §6 — context management):
   `system persona` + `config` + `compact question plan & current index` +
   `rolling_summary of older answered questions` + `last N verbatim messages` + `the new answer`.
4. **Ask the model** with the `interviewer_turn` tool *forced* (`tool_choice`), so it always returns
   structured JSON — never free-form prose:
   ```jsonc
   {
     "reply": "the text to show the candidate",
     "action": "follow_up | next_question | end_interview",
     "current_question_eval": { "score": 0, "note": "…" }   // optional, 0–5
   }
   ```
5. **Apply the `action`** server-side (the branch above):
   - **`follow_up`** — stay on the same question; `reply` is a deeper probe. Increment
     `follow_up_count`. Cap it (e.g. max 2) so the interview keeps moving.
   - **`next_question`** — mark the current question `answered`, store its score/note, advance the
     index; the bot message = short acknowledgement + the next question's text. If no questions
     remain → treat as `end_interview`.
   - **`end_interview`** — go to Phase C.
6. **Save the bot turn** + score + updated statuses with `save_history()`; refresh the
   `rolling_summary` when a question closes.
7. **Return** to the UI: the new bot message(s), the `action`, the `current_question`, and
   `progress`. The UI appends bubbles and updates the sidebar — then the loop repeats on the next
   answer.

### 4.1 How the AI decides follow-up vs. move on

The interviewer persona prompt encodes the rule:

> Ask one question at a time. If the answer is vague, incomplete, or too shallow for the target
> level, ask exactly **one** focused follow-up to probe depth. If the answer is sufficient (or the
> follow-up cap is reached), acknowledge briefly and move to the next question. End when the plan is
> covered or the candidate wants to stop.

Because the next message is computed from the **content of the last answer**, the interview adapts
instead of replaying a fixed script.

### 4.2 Worked example (adaptivity)

```
Bot : Q3 — how would you design rate limiting for a public API?
You : Token-bucket per API key, 429 when empty.
  → model: action = follow_up
           reply  = "Where would you store the counters so limits hold across several servers?"
           (answer was correct but shallow on distributed state → it probes)

You : Redis with per-key TTLs.
  → model: action = next_question
           current_question_eval = { score: 4, note: "solid; didn't mention Redis failure modes" }
           reply  = "Nice. Q4 …"
```

Contrast — if the candidate had said *"I don't know"*:

```
  → model: action = next_question
           current_question_eval = { score: 1, note: "no answer" }
           reply  = "No problem, let's move on. Q4 …"
```

### 4.3 Edge cases

| Situation | Handling |
|---|---|
| "I don't know" / very short answer | One optional nudge, else advance with a low score + note |
| Candidate asks a clarifying question | Treat as `follow_up` (clarify) — do **not** mark answered |
| Skip button | `POST …/skip`: mark `skipped`, advance, no LLM call needed |
| Follow-up cap reached | Force `next_question` even if the answer is still weak |
| End early (End button) | Phase C runs on what's answered; the rest = not attempted |
| LLM / network error | User turn already saved (step 2); return a retryable error |
| Reconnect / page refresh | `GET /api/interviews/{id}` rehydrates the full transcript + statuses |

---

## 5. Phase C — End & evaluate (runs once)

Triggered by **End interview** → `POST /api/interviews/{id}/end` (or when the model returns
`end_interview`).

1. Stop accepting answers (`status = ended`).
2. Make a **separate** LLM call over the transcript + the per-question scores gathered during the
   interview, with the `submit_evaluation` tool *forced* so the output is structured and parseable:
   ```jsonc
   {
     "overall_score": 0,                 // 0–100, a practice score — NOT a hiring verdict
     "readiness": "needs_practice | getting_there | interview_ready",
     "competencies": [{ "name": "Technical depth", "score": 0, "comment": "…" }],  // score 0–5
     "strengths": ["…"],
     "improvements": ["…"],
     "per_question": [{ "question_id": "q1", "score": 0, "feedback": "…" }],
     "summary_text": "…"
   }
   ```
3. Store the summary (`status = summarized`) and show it in the feedback card.

> **Framing:** the summary is **coaching feedback to help the candidate practise** — strengths,
> gaps, and how to improve. It is **not** an automated hire / no-hire decision. AI only synthesises;
> the hiring decision stays with a human.

---

## 6. Context management (why the transcript stays cheap)

A multi-turn interview grows every turn, so the server never blindly resends everything. Each
`/answer` call rebuilds the model context from bounded parts:

```
[ system: interviewer persona ]
[ config: role / level / skills / language / style ]
[ full question plan (short) + which question is current ]
[ rolling_summary: 1–2 lines summarising older answered questions ]   ← compresses the tail
[ recent turns verbatim: last N messages of the current question ]     ← keeps local detail
[ the candidate's newest answer ]
```

- **Recent window** kept verbatim for coherent follow-ups.
- **Older turns** collapsed into `rolling_summary` (per-question one-liners) so token cost stays flat
  as the interview grows. Use `Backend/app/utils/token_utils.py`
  (`estimate_tokens`, `truncate_to_token_budget`) to enforce a budget; swap in a real tokenizer
  later.
- Per-question scores captured during the interview feed Phase C, so the evaluator needn't re-read
  the entire raw transcript.

---

## 7. Why function calling (not plain text)

If the model just replied in prose, the server couldn't reliably tell whether to advance the
question, update the sidebar, or end — the UI state would drift. Forcing a **tool call** gives a
machine-readable decision every turn, so progress and the sidebar stay in sync and control flow is
deterministic. The human-facing text simply rides inside `reply`.

The three function calls in this workflow:

| Function call | When | Purpose |
|---|---|---|
| `interviewer_turn` | Every answer (Phase B, step 4) | Reliable turn control — follow-up vs next vs end |
| `save_history()` | Every turn (steps 2 & 6) | Persist the transcript — *"lưu chat history"* |
| `submit_evaluation` | Once, at the end (Phase C) | Structured feedback — *"function call LLM để đánh giá"* |

---

## 8. End-to-end sequence (all three phases)

```
Start  → POST /interviews        → generate plan (reuse W1) → send Q1
Answer → POST /interviews/{id}/answer  → save → context → interviewer_turn → apply → save → return
  … repeat Phase B until all questions answered / user ends / model ends …
End    → POST /interviews/{id}/end      → submit_evaluation → store summary
View   → GET  /interviews/{id}/summary  → render feedback card
```

See [interview-chatbox-design.md §4](interview-chatbox-design.md) for the full endpoint list and
request/response shapes.
