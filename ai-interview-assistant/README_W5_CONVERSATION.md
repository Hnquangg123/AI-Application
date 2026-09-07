# Workshop 5 - Conversational Interview Mode

W5 keeps the W4 numbered interview plan and adds a more natural turn experience. Sessions start in the existing structured chat mode. During an active interview, the candidate can enable **Conversation mode** from the composer, answer by voice, and receive focused follow-ups grounded in the selected project.

## Implemented

- `InterviewConfigRequest.mode`: `structured` (default) or `conversation`.
- Active sessions can toggle between chat and conversation mode from the composer.
- LangGraph workflow for conversation turns:
  - retrieve up to five indexed project chunks;
  - call the structured interviewer decision model;
  - return a follow-up, advance, or end decision.
- Existing persistence, idempotency, progress, skip, end, and evaluation behavior are reused.
- Two-way browser voice mode speaks each interviewer turn automatically, starts listening after Ari finishes, and submits the candidate's final transcript after four seconds of silence.
- Candidates can submit immediately with an end signal such as "that's all", "I'm done", or "I am done"; the signal is included in the submitted transcript.
- The candidate can interrupt Ari while speaking and switch immediately to listening.
- Browser microphone input uses the Web Speech API with English (`en-US`) in the W5 MVP.
- Text entry remains available when speech recognition is unsupported or microphone permission is denied.
- Existing structured interview mode and legacy stateless chat behavior remain compatible.

## Run

Install backend dependencies from `Backend/requirements.txt` or the backend `pyproject.toml`, then start the backend from `Backend/`:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Start the frontend from `frontend/`:

```bash
npm run dev
```

Use a Chromium-based browser for the most consistent Web Speech API support. Microphone access is optional; typed answers work in every supported browser. The first voice interaction may require a button press because browsers restrict automatic audio playback.

## Current boundaries

- Conversational sessions use browser speech synthesis for interviewer turns and browser speech recognition for candidate answers. Voice mode is English-only in this MVP.
- LangGraph currently orchestrates retrieval and model decision; SQL persistence and idempotency remain in `InterviewService`.
- Project context is retrieved only for `conversation` mode and is not returned directly to the user.
- Durable graph checkpoint storage, backend speech-to-text, streaming responses, and authentication are follow-up work.
