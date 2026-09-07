# Project Structure & Task Ownership — W2 Mock Interview Chatbot

> The scaffold for both sides. `★` = created for W2 (currently a **TODO stub** unless noted).
> Task IDs reference [implementation-tasks.md](implementation-tasks.md).
> Fill in the **Owner** column to assign work per member.

## Tree

```
ai-interview-assistant-master/
├── main.py                         # exists — TODO BE-A2: include interview_router
├── pyproject.toml / requirements.txt / README.md / .env.example
│
├── app/                            # ── BACKEND ──
│   ├── api/
│   │   ├── chat_router.py          # W1 legacy (POST /api/chat)
│   │   └── interview_router.py     ★ TODO BE-J  (endpoints, currently 501)
│   ├── clients/
│   │   ├── openai_client.py        # exists
│   │   └── llm_tools.py            ★ TODO BE-E  (forced tool calls) — build first
│   ├── config/
│   │   ├── settings.py             # exists — TODO BE-A3 (new settings)
│   │   └── logging.py
│   ├── models/
│   │   ├── schemas.py              # W1
│   │   └── interview.py            ★ TODO BE-B  (enums done; models stubbed)
│   ├── prompts/
│   │   ├── system_prompt.txt       # W1 — TODO BE-D4 (retire/repurpose)
│   │   ├── interview_prompt.txt    # W1
│   │   ├── interviewer_system_prompt.txt  ★ TODO BE-D1
│   │   ├── question_plan_prompt.txt       ★ TODO BE-D2 (reuse W1)
│   │   └── evaluation_prompt.txt          ★ TODO BE-D3
│   ├── services/
│   │   ├── chat_service.py         # W1
│   │   ├── question_service.py     ★ TODO BE-F
│   │   ├── interview_service.py    ★ TODO BE-G / BE-H (turn loop + context)
│   │   └── evaluation_service.py   ★ TODO BE-I
│   ├── stores/
│   │   └── session_store.py        ★ TODO BE-C (interface + InMemory + save_history)
│   └── utils/
│       ├── file_utils.py           # exists
│       └── token_utils.py          # exists — reused by BE-H3
│
├── data/                           ★ session JSON snapshots (BE-C4)
│   └── .gitkeep
│
├── tests/
│   ├── test_chat_service.py        # exists — TODO BE-L1 (fix arg mismatch)
│   ├── test_session_store.py       ★ TODO BE-L2 (skipped)
│   ├── test_interview_service.py   ★ TODO BE-L3 (skipped)
│   └── test_evaluation_service.py  ★ TODO BE-L4 (skipped)
│
├── frontend/                       ★ ── FRONTEND ──
│   ├── index.html                  ★ static mockup — VIEWABLE now
│   ├── README.md                   ★
│   ├── styles/main.css             ★ starter theme (done enough for the mock)
│   └── js/
│       ├── api.js                  ★ TODO FE-A2
│       ├── state.js                ★ TODO FE-H
│       ├── app.js                  ★ entry (stub)
│       └── components/
│           ├── setup.js            ★ TODO FE-C
│           ├── chat.js             ★ TODO FE-D
│           ├── sidebar.js          ★ TODO FE-E
│           ├── footer.js           ★ TODO FE-F
│           └── summary.js          ★ TODO FE-G
│
└── docs/
    ├── interview-chatbox-design.md   # UI, API list, data model
    ├── interview-workflow.md         # runtime flow
    ├── implementation-tasks.md       # full task breakdown
    └── project-structure.md          # this file
```

## Ownership — assign a member per area

**Team (10):** 8 on backend (one area each), 2 on frontend (four areas each). Assignments below are a
starting point — swap freely. Organizer: Luan Nguyen Minh (Brian).

### Backend (8 members)
| Area | Files | Tasks | Owner | Status |
|---|---|---|---|---|
| Data models | `models/interview.py` | BE-B | Duc Chau Minh | TODO |
| Session store + save_history | `stores/session_store.py`, `data/` | BE-C | Hiep Doan Quoc | TODO |
| LLM tool calling | `clients/llm_tools.py` | BE-E | Phuc Pham Anh | TODO |
| Question plan (reuse W1) | `services/question_service.py`, `prompts/question_plan_prompt.txt` | BE-F, BE-D2 | Vi Do Hoang | TODO |
| Turn loop + context mgmt | `services/interview_service.py`, `prompts/interviewer_system_prompt.txt` | BE-G, BE-H, BE-D1 | Luan Nguyen Minh (Brian) | TODO |
| Evaluation | `services/evaluation_service.py`, `prompts/evaluation_prompt.txt` | BE-I, BE-D3 | Phong Nguyen Thanh | TODO |
| Endpoints + wiring | `api/interview_router.py`, `main.py`, `config/settings.py` | BE-J, BE-A2, BE-A3 | Tang Le Van (Tank) | TODO |
| Tests | `tests/test_*` | BE-L | Tuan Nguyen Anh (Kevin) | TODO |

### Frontend (2 members)
| Area | Files | Tasks | Owner | Status |
|---|---|---|---|---|
| Theme + shell | `index.html`, `styles/main.css` | FE-A3, FE-B | Quang Hua Nhat (Dylan) | starter done |
| Setup form | `js/components/setup.js` | FE-C | Quang Hua Nhat (Dylan) | TODO |
| Sidebar / progress | `js/components/sidebar.js` | FE-E | Quang Hua Nhat (Dylan) | TODO |
| Summary view | `js/components/summary.js` | FE-G | Quang Hua Nhat (Dylan) | TODO |
| API client | `js/api.js` | FE-A2 | Trieu Vo Dai (Kevin) | TODO |
| State + resume | `js/state.js`, `js/app.js` | FE-H | Trieu Vo Dai (Kevin) | TODO |
| Chat box | `js/components/chat.js` | FE-D | Trieu Vo Dai (Kevin) | TODO |
| Footer actions | `js/components/footer.js` | FE-F | Trieu Vo Dai (Kevin) | TODO |

## Notes
- **Nothing is wired into `main.py` yet** (BE-A2) — the running app is unchanged; the new router
  is import-safe and returns `501` until implemented.
- Backend Python stubs are **import-safe**: functions raise `NotImplementedError`, endpoints return
  `501`, and the skipped tests won't fail `pytest`.
- `frontend/index.html` is a **static mockup** (open it directly). The `js/` stubs turn it live.
- Build order: **BE-E → BE-B/BE-C → BE-F → BE-G → BE-I → BE-J**, FE in parallel against mocked API
  once the contract (SH-1) is agreed. See the milestones in [implementation-tasks.md](implementation-tasks.md#3-suggested-milestones-sequence).
