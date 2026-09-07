# AI Interview Assistant Workshop

MockMate is a full-stack mock AI Interview Assistant organized as a frontend/backend monorepo.

```text
AI_WORKSHOP/
|-- frontend/   # React 19, TypeScript, vinext/Vite UI
|-- Backend/    # FastAPI, OpenAI integration, PostgreSQL, Alembic, and tests
|-- docs/       # Product and workflow specifications
|-- .venv/      # Shared local Python virtual environment
`-- README.md
```

## Run locally

Start PostgreSQL and the API from `Backend`:

```powershell
docker compose up -d postgres
..\.venv\Scripts\alembic.exe upgrade head
..\.venv\Scripts\uvicorn.exe main:app --reload
```

In another terminal, start the frontend from `frontend`:

```powershell
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000/api`. To use another API URL, copy
`frontend/.env.example` to `frontend/.env.local` and update
`NEXT_PUBLIC_API_BASE_URL`.

See `Backend/README.md` and `frontend/README.md` for validation commands and more details.
