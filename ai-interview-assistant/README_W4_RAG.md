# Workshop 4 — Project Knowledge with RAG

W4 adds **project-aware interviews** to MockMate. Users can create a project, organize its
documentation into pages, add text and architecture diagrams, build a vector index, and select the
project when starting an interview. MockMate retrieves the most relevant project context and adds
one project deep-dive question at the end of the normal interview plan.

Text embeddings run locally. Images are analyzed by the existing `gpt-4o-mini` endpoint because a
vision model understands diagram labels, arrows, events, and component relationships more accurately
than a generic local image-captioning model.

---

## 1. What we built

- A **Manage Projects** area in the frontend.
- A dedicated project workspace at `/projects/{project_id}`, styled like a documentation site.
- Project pages containing ordered **text** and **image** blocks.
- Background indexing for individual pages or a complete project.
- Local, multilingual, 384-dimensional text embeddings.
- PostgreSQL `pgvector` storage with an HNSW cosine index.
- Semantic retrieval when a project is selected for an interview.
- One project-specific question appended to the end of the interview.
- Background preparation of the project question so Start Interview does not wait for the local
  embedding model to load.

---

## 2. Architecture

```text
Project workspace
  → create/edit pages
    → add text or image blocks
      → Build RAG
        → background indexing
          ├─ text  → chunk directly
          └─ image → gpt-4o-mini vision → English technical description
        → local MiniLM embedding (384 dimensions)
        → PostgreSQL project_data.embedding (pgvector)

Start Interview with a project
  → generate the normal N-question plan immediately
  → append one fallback project question at position N
  → return the interview response
  → background task
    → embed the retrieval query locally
    → cosine search for the five closest project chunks
    → gpt-4o-mini generates one grounded project question
    → replace the final fallback question while it is still pending
```

The image itself is sent only to the configured vision endpoint during indexing. The resulting
English description is embedded locally; the application does not call an external embedding API.

---

## 3. Data model

### `projects`

Stores project-level information.

| Column | Purpose |
|---|---|
| `id` | UUID primary key. |
| `name` | Project display name. |
| `description` | Short project overview; also included in project-question context. |
| `created_at`, `updated_at` | Audit timestamps. |

### `project_sections`

Each row is one documentation page inside a project.

| Column | Purpose |
|---|---|
| `project_id` | Parent project. |
| `title` | Page title. |
| `slug` | URL-friendly page identifier, unique within the project. |
| `content` | JSONB document containing ordered text/image blocks. |
| `sort_order` | Sidebar ordering. |
| `indexing_status` | `pending`, `processing`, `ready`, or `failed`. |
| `indexing_error` | Last indexing error, when present. |

Example page content:

```json
{
  "blocks": [
    {
      "type": "text",
      "value": "Order Service writes orders to PostgreSQL."
    },
    {
      "type": "image",
      "value": "data:image/png;base64,...",
      "caption": "Order processing architecture"
    }
  ]
}
```

### `project_data`

Stores the searchable chunks produced by indexing.

| Column | Purpose |
|---|---|
| `project_id` | Parent project. |
| `project_section_id` | Source page; nullable for legacy direct project data. |
| `chunk_index` | Stable order within the indexed page. |
| `source_type` | `text` or `image`. |
| `source_content` | Source/chunk content. |
| `extracted_text` | Text that is embedded and supplied to RAG. |
| `embedding` | `vector(384)`. |
| `metadata` | Section title, slug, block index, chunk index, and caption. |
| `status` | `pending`, `processing`, `ready`, or `failed`. |
| `error` | Processing error, when present. |

Deleting a project deletes its pages and vector data. Deleting a page deletes the vectors generated
from that page.

---

## 4. Models used

| Task | Model | Runs where |
|---|---|---|
| Text and query embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Local backend |
| Image/diagram to English text | `gpt-4o-mini` | Configured OpenAI-compatible endpoint |
| Interview plans and project questions | `gpt-4o-mini` | Configured OpenAI-compatible endpoint |
| Vector similarity | PostgreSQL pgvector cosine distance | Local database |

MiniLM returns normalized 384-dimensional vectors. The same model must be used for both document
chunks and retrieval queries; changing the model or dimensions requires a migration and complete
reindex.

The vision prompt requires English output, exact transcription of visible labels, explicit
`source -> target` relationships, API paths, event names, data stores, and data flow. It also tells
the model not to invent details or include the file name.

---

## 5. Prerequisites

Each teammate running locally needs:

- Python 3.11+ and Node.js 20+.
- PostgreSQL with the `vector` extension; the supplied Docker setup provides it.
- An OpenAI-compatible API key/endpoint with access to `gpt-4o-mini` and image input.
- Enough disk/RAM for the local MiniLM embedding model.
- Internet access on the first embedding run so Hugging Face can populate the local model cache.

No OpenAI embedding-model permission is required. W4 does not call `text-embedding-3-small`.

---

## 6. Run the backend

From the repository root, create a short virtual-environment path on Windows to avoid the long-path
limit encountered by large packages such as PyTorch:

```cmd
py -m venv C:\venvs\mockmate
C:\venvs\mockmate\Scripts\python.exe -m pip install --upgrade pip
C:\venvs\mockmate\Scripts\python.exe -m pip install -r Backend\requirements.txt
```

Start PostgreSQL, apply all migrations, and run FastAPI:

```cmd
cd Backend
docker compose up -d postgres
C:\venvs\mockmate\Scripts\alembic.exe upgrade head
C:\venvs\mockmate\Scripts\python.exe -m uvicorn main:app --reload
```

Check the API:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

Important migrations for W4:

- `d7e1c2f4a901_add_projects_and_project_data.py`
- `e8f2a3b5c012_use_pgvector_for_project_data.py`
- `f9a3b4c6d123_add_project_sections.py`
- `a0b4c5d7e234_use_local_rag_embeddings.py`

The last migration changes embeddings from 1536 to 384 dimensions and marks existing project data
as pending. Run **Build RAG** again after applying it.

---

## 7. Run the frontend

```cmd
cd frontend
npm install
npm run dev
```

Open the frontend, then select **Manage Projects** in the header. Clicking a project opens its
dedicated documentation workspace at `/projects/{project_id}`.

---

## 8. Build project knowledge

1. Open **Manage Projects**.
2. Create a project with a name and description.
3. Click the project to open its documentation workspace.
4. Add pages such as Overview, Architecture, Data Flow, Deployment, or Failure Handling.
5. Add text and image blocks to each page.
6. Save the page.
7. Click **Build RAG** to queue indexing.
8. Wait until page/data status becomes `ready`.

Saving a non-empty page also queues indexing for that page. **Build RAG** is useful when the model,
chunking logic, source content, or vector dimensions have changed and all pages must be rebuilt.

### Indexing behavior

- Text is cleaned and split into chunks of at most approximately 1,800 characters.
- Adjacent text chunks overlap by 200 characters to preserve context.
- Images are sent as base64 image inputs to `gpt-4o-mini`.
- Image descriptions are generated in English for consistent technical retrieval.
- All chunks are embedded in one batch for a page.
- Existing vectors for that page are replaced only after extraction and embedding succeed.
- A failure sets the page status to `failed` and stores the error message.

---

## 9. Start a project interview

On the interview setup screen, choose a project from the project dropdown and click **Start My
Interview**.

The selected `num_questions` remains the number of normal interview questions. Selecting a project
adds one extra question at the end:

```text
total questions = num_questions + 1 project question
```

The initial request does not perform vector retrieval. It creates the normal plan and a valid
fallback project question, commits the session, and returns it to the frontend. A FastAPI background
task then performs retrieval and updates the final question.

The retrieval query has this shape:

```text
{job_role} {skills} project architecture interview
```

The retriever embeds that query locally and returns at most five ready chunks ordered by pgvector
cosine distance. The project description is prepended to those chunks. `gpt-4o-mini` then creates
exactly one question grounded only in that context.

The project-question prompt may test:

- Architecture and component responsibilities.
- Implementation choices and trade-offs.
- Data flow and event flow.
- Reliability and consistency.
- Failure scenarios and recovery.

The generated question follows the selected interview language. Its `skill_tag` must be null or one
of the configured skills, and its preferred type is `technical` or `system_design`.

If retrieval or generation fails, or if the final question is already current, the valid fallback
question remains unchanged. The background task never changes a question the candidate is already
answering.

> FastAPI `BackgroundTasks` are in-process and not a durable job queue. This is suitable for the
> workshop. A production deployment should use Celery, RQ, Dramatiq, or another persistent worker.

---

## 10. Project API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/projects` | List projects with pages and index status. |
| `POST` | `/api/projects` | Create a project. |
| `GET` | `/api/projects/{project_id}` | Get one project. |
| `PATCH` | `/api/projects/{project_id}` | Update name/description. |
| `DELETE` | `/api/projects/{project_id}` | Delete project, pages, and vectors. |
| `GET` | `/api/projects/{project_id}/sections` | List project pages. |
| `POST` | `/api/projects/{project_id}/sections` | Create a page. |
| `GET` | `/api/projects/{project_id}/sections/{section_id}` | Get a page. |
| `PATCH` | `/api/projects/{project_id}/sections/{section_id}` | Update and queue a page. |
| `DELETE` | `/api/projects/{project_id}/sections/{section_id}` | Delete a page. |
| `POST` | `/api/projects/{project_id}/sections/{section_id}/index` | Queue one page for indexing. |
| `POST` | `/api/projects/{project_id}/reindex` | Queue the entire project. |
| `POST` | `/api/projects/{project_id}/data` | Add legacy direct text/image data. |

`POST /api/interviews` accepts an optional `project_id`. The UUID is serialized as a JSON string
before the interview configuration is stored.

---

## 11. Configuration

Settings are defined in `Backend/app/config/settings.py` and can be overridden in `Backend/.env`.

| Env var | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | required | API credential for chat and vision. |
| `OPENAI_BASE_URL` | OpenAI default when unset | OpenAI-compatible gateway URL. |
| `OPENAI_MODEL_CHAT` | `gpt-4o-mini` | Interview plan, turn, and evaluation model. |
| `OPENAI_CHAT_API` | `auto` | Select Responses or Chat Completions behavior. |
| `OPENAI_TIMEOUT_SECONDS` | `30` | API request timeout. |
| `RAG_EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Local document/query embedding model. |
| `RAG_EMBEDDING_DIMENSIONS` | `384` | Must match the pgvector column. |
| `RAG_VISION_MODEL` | `gpt-4o-mini` | Image and diagram extraction model. |
| `RAG_DEVICE` | `cpu` | Embedding device; use `cuda:0` when supported. |

---

## 12. QuickCart sample

The repository includes a ready-to-use sample:

```text
samples/rag/
├─ README.md
├─ quickcart-project.txt
└─ quickcart-architecture.png
```

Create this project:

- Name: `QuickCart Order Platform`
- Description: `Event-driven e-commerce order processing with PostgreSQL, Kafka, inventory
  reservation, and notifications.`
- Add the contents of `quickcart-project.txt` as text.
- Upload `quickcart-architecture.png` as an image block.

For the diagram, the extracted description should identify this flow:

```text
Web App --REST /orders--> API Gateway -> Order Service -> PostgreSQL
Order Service --OrderCreated--> Kafka -> Inventory Service
                                      -> Notification Service
```

---

## 13. Files changed in W4

**Backend**

- `app/models/project.py` — project, page, and vector models.
- `app/models/schemas.py` — project/page request and response schemas plus `project_id`.
- `app/api/project_router.py` — project/page CRUD and indexing endpoints.
- `app/services/project_service.py` — chunking, indexing, and cosine retrieval.
- `app/services/local_rag_service.py` — local embeddings and GPT-4o-mini image extraction.
- `app/services/interview_service.py` — project selection and background final-question workflow.
- `app/services/interview_ai_service.py` — grounded project-question generation.
- `app/config/settings.py` — RAG model settings.
- `migrations/versions/*project*`, `*pgvector*`, `*local_rag*` — W4 schema changes.

**Frontend**

- `app/page.tsx` — Manage Projects navigation and project dropdown during setup.
- `app/projects/[projectId]/page.tsx` — project documentation workspace.
- `lib/api.ts` — project/page/indexing API client.
- `lib/i18n.ts` — English and Vietnamese project-management labels.
- `app/globals.css` — project workspace and page-editor styling.

---

## 14. Validation

Run backend tests:

```cmd
cd Backend
C:\venvs\mockmate\Scripts\python.exe -m pytest -q
```

The suite covers the normal interview journey and creating an interview with a selected project,
including UUID JSON serialization and the final project question.

Run frontend checks:

```cmd
cd frontend
npm run lint
```

---

## 15. Troubleshooting

- **`type UUID is not JSON serializable` when starting an interview** — update to the W4 version of
  `interview_service.py`; it stores `config.model_dump(mode="json")`.
- **`expected 1536 dimensions, not 384`** — run `alembic upgrade head`, restart the backend, and
  click **Build RAG**.
- **Embedding model loads on Start Interview** — this is expected for semantic retrieval, but it now
  happens in the background. It is cached once per backend process.
- **Embedding model loads repeatedly** — check for backend restarts, `uvicorn --reload` file changes,
  or multiple workers. Each process owns a separate in-memory model cache.
- **First embedding run is slow** — Hugging Face downloads and caches MiniLM. Later calls reuse the
  local cache.
- **Image description is too generic** — confirm `RAG_VISION_MODEL=gpt-4o-mini`, restart the backend,
  and rebuild the page. Old BLIP-generated vectors are not updated automatically.
- **Image indexing returns 401/403/404** — verify `OPENAI_API_KEY`, `OPENAI_BASE_URL`, model access,
  and that the gateway supports image input for `gpt-4o-mini`.
- **Project page remains `processing`** — inspect the backend log. In-process background tasks do not
  survive a backend restart; click **Build RAG** again.
- **Project question stays generic** — ensure at least one page is `ready`. If no vector data exists,
  retrieval returns immediately and the fallback question is intentionally preserved or generated
  from the project description.
- **`New-Item` is not recognized** — that is a PowerShell command. In Command Prompt use
  `mkdir C:\venvs` instead.
- **PyTorch installation fails with a long path error** — keep the virtual environment at a short
  path such as `C:\venvs\mockmate`, or enable Windows Long Path support.

---

## 16. Current workshop limitations

- Only text and image page blocks are supported.
- Images are currently stored as data URLs in JSON/database rows; production systems should use
  object storage and persist only URLs plus metadata.
- Image extraction sends the image to the configured vision API; do not upload sensitive diagrams
  unless that endpoint is approved for the data.
- Background tasks are in-process and have no retry queue.
- Retrieval uses a fixed top-five result count and does not yet include reranking or citations in the
  interview UI.
- Project context is used for coaching questions, not hiring decisions.
