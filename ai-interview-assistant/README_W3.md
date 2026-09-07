# Workshop 3 — Voice Interview Simulator (Text-to-Speech)

W3 adds **voice output** to the Mock Interview Chatbot. Every question the AI interviewer asks now
has a **speaker icon**; clicking it plays that question aloud. The audio is synthesized in the
**backend** by a local Hugging Face model (**Microsoft SpeechT5**) and streamed to the browser.

> Nothing else in the interview flow changed — this is purely additive. If TTS is turned off or the
> model isn't available, the app works exactly as before.

---

## 1. What we built

- A **local TTS service** in the backend that loads SpeechT5 once and turns question text into
  speech (WAV).
- A **new endpoint** that returns the audio for a single interviewer message.
- **Disk + browser caching** so each question is synthesized at most once.
- A **speaker button** on every AI message in the chat (live interview *and* past sessions), with
  play / stop states and EN/VI labels.

### How it works

```
Click 🔊 on a question
  → GET /api/interviews/{session_id}/messages/{message_id}/audio?voice=<index>
    → backend loads the question text from the DB
      → cache hit?  → serve the stored .wav
        cache miss? → SpeechT5 synthesizes it → save to data/tts/ → serve
  → browser plays the WAV (and caches it via Cache-Control headers)
```

---

## 2. Prerequisites

Each teammate running locally needs:

- **Python 3.11+** and **Node.js 20+**
- **PostgreSQL** (via `Backend/compose.yaml`, or your own)
- An **OpenAI API key** (still used for question generation, interview turns, and evaluation)
- **The SpeechT5 model + libraries** (CPU is fine — no GPU required):
  `transformers`, `torch`, `soundfile`, `sentencepiece`.
  Models: `microsoft/speecht5_tts` and `microsoft/speecht5_hifigan` (vocoder). The voice uses a
  built-in generated speaker embedding — no extra dataset download needed.

---

## 3. Run the backend

From the repo root:

```powershell
cd Backend
..\.venv\Scripts\Activate.ps1          # create once: python -m venv ..\.venv

pip install -r requirements.txt        # transformers / torch / soundfile / sentencepiece / datasets
copy .env.example .env                 # set OPENAI_API_KEY (and DATABASE_URL if needed)

docker compose up -d postgres
alembic upgrade head

uvicorn main:app --reload
```

Check it's up:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

The first speak click loads the model and speaker dataset (a few seconds). To preload at startup,
set `TTS_WARM_UP_ON_START=true` in `.env`.

## 4. Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

The UI calls `http://localhost:8000/api` by default. Override with `NEXT_PUBLIC_API_BASE_URL` in
`frontend/.env.local`.

## 5. Using the voice feature

Start a practice; next to each **ARI** (interviewer) message you'll see a speaker icon. Click it to
hear the question, click again to stop. Only one clip plays at a time.

---

## 6. Configuration

TTS settings live in `Backend/app/config/settings.py`, overridable via `Backend/.env` (env var names
are the field names in upper case):

| Env var | Default | Purpose |
|---|---|---|
| `TTS_ENABLED` | `true` | Turn the feature on/off. |
| `TTS_MODEL_ID` | `microsoft/speecht5_tts` | The SpeechT5 TTS model. |
| `TTS_VOCODER_ID` | `microsoft/speecht5_hifigan` | The vocoder that turns spectrograms into audio. |
| `TTS_DEVICE` | `cpu` | Inference device. `cuda:0` (NVIDIA GPU) or `mps` (Apple Silicon / M1). On a Mac, `cuda` won't work — use `mps`. |
| `TTS_SPEAKER_INDEX` | `7306` | The voice (seed for the generated speaker embedding). |
| `TTS_SPEAKER_EMBEDDING_PATH` | `(unset)` | Optional `.npy`/`.pt` 512-dim x-vector for a real voice. |
| `TTS_NORMALIZE` | `true` | Peak-normalize the audio so it's as loud as possible without clipping. |
| `TTS_GAIN` | `1.0` | Extra volume multiplier — raise (e.g. `1.3`) for louder; too high distorts. |
| `TTS_CACHE_DIR` | `data/tts` | Where synthesized WAV files are cached. |
| `TTS_WARM_UP_ON_START` | `false` | Preload the model when the API starts. |

**Voice:** SpeechT5 uses a 512-dim speaker embedding. By default we generate a stable voice from
`TTS_SPEAKER_INDEX` (change it, or pass `?voice=<n>`, for a different voice). For a natural real
voice, point `TTS_SPEAKER_EMBEDDING_PATH` at a 512-dim x-vector saved as `.npy` or `.pt`.

**Language:** SpeechT5 is an **English** model. Vietnamese interview text will be mispronounced —
use English interviews for good audio (or add a multilingual model later).

---

## 7. Test the endpoint / the model directly

Fastest check (bypasses the web layer, prints the real error if any) — from `Backend/` with the venv active:

```powershell
python -c "from app.services import tts_service; print(len(tts_service.get_or_create_audio('Hello, this is a test.', language='en')))"
```

Or via the API, using ids from a real session:

```powershell
Invoke-RestMethod "http://localhost:8000/api/interviews/<SESSION_ID>" | Select-Object -ExpandProperty messages
Invoke-WebRequest "http://localhost:8000/api/interviews/<SESSION_ID>/messages/<MESSAGE_ID>/audio" -OutFile question.wav
```

Status codes: `200` WAV audio · `404` unknown/non-interviewer message · `400` empty/too-long text ·
`503` TTS disabled or libraries missing · `502` synthesis failed (the response body and the uvicorn
console now show the real error).

---

## 8. Files changed in W3

**Backend**
- `app/services/tts_service.py` — *new*; loads SpeechT5 once, caches WAV to disk, synthesizes speech.
- `app/api/interview_router.py` — *new* `GET /{session_id}/messages/{message_id}/audio` endpoint.
- `app/config/settings.py` — TTS settings.
- `main.py` — optional model warm-up on startup.
- `requirements.txt` — `transformers`, `torch`, `soundfile`, `sentencepiece`.

**Frontend**
- `lib/api.ts` — `messageAudioUrl(...)` helper.
- `app/page.tsx` — speaker icon + audio playback on AI messages.
- `lib/i18n.ts` — EN/VI labels for the speak button.

---

## 9. Troubleshooting

- **`503` "TTS libraries are not installed"** — install
  `transformers torch soundfile sentencepiece datasets` in the venv running the API, or set
  `TTS_ENABLED=false`.
- **First click is slow** — the model + speaker dataset are downloading/loading. Set
  `TTS_WARM_UP_ON_START=true` to load at startup.
- **`502` on the first real run** — the response body and the uvicorn console print the actual Python
  error; read that. Common ones: a missing package (install it) or no network for the model download.
- **Vietnamese sounds wrong** — SpeechT5 is English-only; use English interviews for voice.
- **Want a different voice** — change `TTS_SPEAKER_INDEX` (or pass `?voice=<index>`).
- **Audio too quiet / changed volume but it sounds the same** — raise `TTS_GAIN` (e.g. `1.3`), and
  delete the cached WAVs in `Backend/data/tts/` so questions re-synthesize at the new level (the
  cache keeps the old audio otherwise).
- **Have a GPU** — set `TTS_DEVICE=cuda:0` (NVIDIA) or `TTS_DEVICE=mps` (Apple M1/M2/M3). On a Mac,
  `cuda` won't work; use `mps`. SpeechT5 on MPS is hit-or-miss — if it 502s, go back to `cpu`.
- **CPU is slow the first time** — the first click downloads the model (~700 MB) and loads it; set
  `TTS_WARM_UP_ON_START=true` so that happens at startup, and note repeat plays are served from cache.

---

## 10. Notes

- Output is **WAV** at 16 kHz (widest browser support).
- The interview logic, database, and evaluation are unchanged from W2.
- Feedback is coaching-oriented practice guidance — not a hiring decision.
