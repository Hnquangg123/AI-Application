# AI Interview Assistant Backend

FastAPI backend and PostgreSQL persistence for the mock AI Interview Assistant.

## Structure

```text
Backend/
├── app/                  # API, services, models, prompts, and database setup
├── migrations/           # Alembic database migrations
├── scripts/              # Local utility scripts
├── tests/                # Backend tests
├── compose.yaml          # PostgreSQL for Rancher Desktop
├── alembic.ini
├── main.py
├── pyproject.toml
└── requirements.txt
```

## Setup

Run these commands from `AI_WORKSHOP/Backend`.

```powershell
# Install backend dependencies into the repository virtual environment
..\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Start PostgreSQL in Rancher Desktop
# Rancher Desktop should use the dockerd (moby) engine.
docker compose up -d postgres
docker compose ps

# Apply schema migrations
..\.venv\Scripts\alembic.exe upgrade head

# Run tests
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider

# Start the API
..\.venv\Scripts\uvicorn.exe main:app --reload
```

Verify the API and database:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

The default mock-development database is exposed at `localhost:5432`. Its data is stored in the named volume `ai_workshop_interview_postgres_data`.

## Environment

Copy `.env.example` to `.env` and replace mock values as needed. The checked-in Compose defaults are intended for local development only.

## Database commands

```powershell
docker compose logs -f postgres
docker compose stop postgres
docker compose down
..\.venv\Scripts\alembic.exe check
```

`docker compose down` preserves the database volume. Use `--volumes` only when intentionally deleting local database data.