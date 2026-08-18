# Assignment 09 - Laptop Consultant Chatbot

A retrieval-augmented laptop recommendation chatbot built with Azure OpenAI,
the official OpenAI Python library, and ChromaDB. The program embeds a small
laptop catalog, retrieves products that match each user's requirements, and
asks GPT-4o-mini to produce a grounded recommendation.

The final assignment checklist requires a single Python code file and three
automated mock queries, so the application runs as a script and never calls
`input()`.

## Features

- Uses Azure OpenAI `text-embedding-3-small` embeddings.
- Stores and searches laptop descriptions with an in-memory ChromaDB collection.
- Uses Azure OpenAI Chat Completions with the `GPT-4o-mini` deployment.
- Processes the three assignment queries automatically.
- Grounds every recommendation in the retrieved laptop catalog.
- Validates configuration and reports failures without displaying API keys.
- Exits automatically after all three recommendations are printed.

## How it works

For each query, the application follows this retrieval-augmented generation
(RAG) flow:

1. Embed the three sample laptop descriptions.
2. Store the vectors, descriptions, names, and tags in ChromaDB.
3. Embed the current user query.
4. Retrieve the three most relevant laptops from ChromaDB.
5. Format the retrieved records as context.
6. Send the requirements and context to GPT-4o-mini.
7. Print the grounded recommendation and continue to the next mock query.

## Project structure

```text
assignment-09/
|-- laptop_consultant.py  # Complete assignment implementation
|-- requirements.txt      # Python dependencies
|-- .gitignore            # Secret, cache, and environment exclusions
`-- README.md             # Setup and usage documentation
```

All application code is contained in `laptop_consultant.py`, as required by the
submission checklist.

## Requirements

- Python 3.10 or later
- Access to the course Azure OpenAI-compatible gateway
- A fresh API key that can access both deployments
- Deployments named:
  - `text-embedding-3-small`
  - `GPT-4o-mini`

The configured standard endpoint is:

```text
https://aiportalapi.stu-platform.live/jpe
```

This project intentionally uses the standard, no-cache endpoint so requests
are served directly by the model.

## Installation

### 1. Create and activate a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

The script reads the six environment variables specified by the assignment.
The embedding and chat clients use separate variables even though this course
environment supplies one shared key and endpoint.

| Variable | Purpose | Course value |
| --- | --- | --- |
| `AZURE_OPENAI_EMBEDDING_API_KEY` | Embedding client key | Set locally; never commit |
| `AZURE_OPENAI_EMBEDDING_ENDPOINT` | Embedding endpoint | `https://aiportalapi.stu-platform.live/jpe` |
| `AZURE_OPENAI_EMBED_MODEL` | Embedding deployment | `text-embedding-3-small` |
| `AZURE_OPENAI_LLM_API_KEY` | Chat client key | Same fresh key; never commit |
| `AZURE_OPENAI_LLM_ENDPOINT` | Chat endpoint | `https://aiportalapi.stu-platform.live/jpe` |
| `AZURE_OPENAI_LLM_MODEL` | Chat deployment | `GPT-4o-mini` |

### PowerShell

Replace `<your-rotated-api-key>` with a fresh key. Do not reuse a key that has
been pasted into chat, committed to Git, or otherwise exposed.

```powershell
$env:AZURE_OPENAI_EMBEDDING_API_KEY = "<your-rotated-api-key>"
$env:AZURE_OPENAI_EMBEDDING_ENDPOINT = "https://aiportalapi.stu-platform.live/jpe"
$env:AZURE_OPENAI_EMBED_MODEL = "text-embedding-3-small"

$env:AZURE_OPENAI_LLM_API_KEY = $env:AZURE_OPENAI_EMBEDDING_API_KEY
$env:AZURE_OPENAI_LLM_ENDPOINT = $env:AZURE_OPENAI_EMBEDDING_ENDPOINT
$env:AZURE_OPENAI_LLM_MODEL = "GPT-4o-mini"
```

### macOS or Linux

```bash
export AZURE_OPENAI_EMBEDDING_API_KEY="<your-rotated-api-key>"
export AZURE_OPENAI_EMBEDDING_ENDPOINT="https://aiportalapi.stu-platform.live/jpe"
export AZURE_OPENAI_EMBED_MODEL="text-embedding-3-small"

export AZURE_OPENAI_LLM_API_KEY="$AZURE_OPENAI_EMBEDDING_API_KEY"
export AZURE_OPENAI_LLM_ENDPOINT="$AZURE_OPENAI_EMBEDDING_ENDPOINT"
export AZURE_OPENAI_LLM_MODEL="GPT-4o-mini"
```

Environment variables set this way last only for the current terminal session.

## Usage

Run the program after activating the virtual environment and setting all six
variables:

```bash
python laptop_consultant.py
```

The script automatically processes these three queries:

1. A lightweight laptop with long battery life for business trips.
2. A gaming laptop with the best available graphics card.
3. A budget laptop for student tasks and general browsing.

Expected output structure:

```text
============================================================
User input: I want a lightweight laptop with long battery life for business trips.

LLM Recommendation:

<grounded recommendation from GPT-4o-mini>
============================================================

...two more query and recommendation blocks...

Completed all three laptop recommendation queries.
```

The exact recommendation wording may vary between runs because the standard
endpoint does not use semantic caching.

## Main functions

- `AppConfig.from_environment()` validates the six required variables.
- `create_clients()` creates the embedding and chat Azure OpenAI clients.
- `get_embedding()` requests an embedding vector.
- `create_laptop_collection()` embeds and upserts the laptop catalog.
- `retrieve_laptops()` performs vector similarity search.
- `build_context()` formats retrieved products for the prompt.
- `ask_llm()` requests a grounded laptop recommendation.
- `run_recommendations()` executes the three automated scenarios.

## Troubleshooting

### Missing required environment variables

Set all six variables in the same terminal before running the program. The
error message lists missing variable names but never their values.

### Authentication failed or HTTP 401/403

Verify that the key is current and that it has access to both course
deployments. Rotate any key that has been exposed.

### HTTP 404 or deployment error

Confirm the exact deployment names and capitalization:
`text-embedding-3-small` and `GPT-4o-mini`. Also confirm that the standard
endpoint is copied exactly.

### Connection error

Check the internet connection, VPN or proxy requirements, and course gateway
availability.

### `ModuleNotFoundError`

Activate the intended virtual environment and reinstall the requirements:

```bash
python -m pip install -r requirements.txt
```

## Security notes

- Never place real API keys in `laptop_consultant.py` or `README.md`.
- Never commit `.env` files; they are excluded by `.gitignore`.
- Treat any key pasted into chat or source control as compromised and rotate it.
- Error handling intentionally avoids printing request headers or credentials.

## Assignment checklist

| Requirement | Implementation |
| --- | --- |
| Environment variable setup with placeholders | Documented above and validated by `AppConfig` |
| Azure OpenAI embedding client | `AzureOpenAI` with `text-embedding-3-small` |
| ChromaDB storage and retrieval | In-memory collection with vector upsert and query |
| Azure OpenAI chat completion | `client.chat.completions.create()` with `GPT-4o-mini` |
| Three sample laptops | Included exactly in `LAPTOPS` |
| Three automated mock queries | Included exactly in `USER_QUERIES` |
| No interactive `input()` loop | Queries run automatically in `run_recommendations()` |
| Single Python code file | All application code is in `laptop_consultant.py` |
