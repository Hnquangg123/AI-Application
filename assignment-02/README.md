# Assignment 02 - Automotive Work-Instruction Generator

This project implements a prompt-driven AI assistant that converts high-level automotive engineering tasks into consistent, shop-floor work instructions. It automatically processes the five task descriptions supplied in Assignment 02 and saves the generated results in a readable Markdown report.

The solution uses prompt engineering and an LLM directly. It does not use retrieval-augmented generation (RAG), a vector database, or manual `input()`.

## Features

- Processes all five assignment tasks from a fixed list in `main.py`.
- Supports Azure OpenAI and an OpenAI-compatible gateway.
- Requests safety precautions, required tools, numbered steps, and acceptance criteria.
- Uses `temperature=0` for consistent output.
- Prevents the model from inventing missing torque, pressure, cure-time, calibration, or software specifications.
- Writes the report atomically, so an incomplete API run does not replace a valid report.
- Keeps API keys and endpoint details out of generated files and console output.

> **Important:** Generated instructions are drafts. A qualified manufacturing engineer and safety representative must validate them before use in production.

## Project structure

```text
assignment-02/
|-- main.py                            # Complete assignment source code
|-- generated_work_instructions.md     # Five generated task/result pairs
|-- requirements.txt                   # Reproducible Python dependency
|-- .gitignore                         # Excludes secrets and local files
`-- README.md                           # Setup, usage, and reflection
```

## Requirements

- Python 3.10 or later
- Network access to the selected LLM endpoint
- Either Azure OpenAI credentials or credentials for an OpenAI-compatible gateway

## Installation

Create and activate a virtual environment, then install the dependency.

### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Bash

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuration

Configuration is read only from environment variables. Never place a real API key in `main.py`, `README.md`, or Git.

### Option 1: Azure OpenAI (default)

Azure mode follows the implementation requested by the assignment PDF.

PowerShell:

```powershell
$env:LLM_PROVIDER = "azure"
$env:AZURE_OPENAI_API_KEY = "<your-azure-api-key>"
$env:AZURE_OPENAI_ENDPOINT = "https://<resource-name>.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "<your-deployment-name>"
$env:AZURE_OPENAI_API_VERSION = "2024-07-01-preview"
python main.py
```

Bash:

```bash
export LLM_PROVIDER="azure"
export AZURE_OPENAI_API_KEY="<your-azure-api-key>"
export AZURE_OPENAI_ENDPOINT="https://<resource-name>.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="<your-deployment-name>"
export AZURE_OPENAI_API_VERSION="2024-07-01-preview"
python main.py
```

`AZURE_OPENAI_API_VERSION` is optional and defaults to `2024-07-01-preview`.

### Option 2: OpenAI-compatible gateway

Use this mode when the course or organization supplies an OpenAI-compatible base URL rather than a standard Azure resource URL.

PowerShell:

```powershell
$env:LLM_PROVIDER = "gateway"
$env:OPENAI_API_KEY = "<your-gateway-api-key>"
$env:OPENAI_BASE_URL = "<your-gateway-base-url>"
$env:OPENAI_MODEL = "gpt-4o-mini"
$env:OPENAI_AUTH_MODE = "bearer"
python main.py
```

Bash:

```bash
export LLM_PROVIDER="gateway"
export OPENAI_API_KEY="<your-gateway-api-key>"
export OPENAI_BASE_URL="<your-gateway-base-url>"
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_AUTH_MODE="bearer"
python main.py
```

`OPENAI_MODEL` is optional and defaults to `gpt-4o-mini`. `OPENAI_AUTH_MODE` is also optional and defaults to standard `bearer` authentication. Set it to `litellm` only when the gateway documentation requires the additional `X-Litellm-Key` header.

## Usage and output

Run the program once after configuration:

```text
python main.py
```

The program automatically submits these five task categories:

1. High-voltage battery-module installation
2. ADAS radar-sensor calibration
3. Anti-corrosion sealant application
4. Coolant-system leak testing
5. Infotainment ECU programming and validation

After all five API calls succeed, the program creates or replaces `generated_work_instructions.md`. The report contains generation metadata, a task summary table, and a detailed instruction set for every task. It never records the API key or endpoint.

## Prompt-engineering approach

The system prompt assigns the model the role of a senior automotive manufacturing supervisor and technical writer. It also enforces a predictable response structure:

- Safety precautions
- Required tools and equipment
- Numbered work instructions
- Acceptance criteria

The prompt explicitly tells the model not to invent engineering values. If the task does not provide a torque, pressure, cure time, tolerance, software version, or other numeric specification, the response must refer to the approved engineering specification and require confirmation before work begins.

## Error handling

The program exits with status code `1` and an actionable message when:

- A required environment variable is missing.
- `LLM_PROVIDER` is not `azure` or `gateway`.
- The `openai` package is not installed.
- Authentication, endpoint, deployment, model, or network configuration fails.
- The selected gateway authentication mode is not `bearer` or `litellm`.
- The API returns empty content or omits a required report section.

The underlying exception is not printed, reducing the risk of exposing sensitive endpoint or authentication details.

## Troubleshooting

### Missing environment variables

Read the variable names in the error message and configure them in the same terminal session used to run `python main.py`.

### Authentication error

Verify that the key belongs to the configured endpoint and has not expired or been revoked. Rotate any key that was pasted into source code, a ticket, or a chat.

### Unsupported model or deployment

- Azure mode requires the deployment name, not just the underlying model family.
- Gateway mode requires the model identifier exposed by that gateway.

### Endpoint or 404 error

Confirm that `AZURE_OPENAI_ENDPOINT` is the Azure resource root or that `OPENAI_BASE_URL` is the exact OpenAI-compatible base URL supplied by the provider.

## Reflection

Prompt-driven AI can reduce the time needed to turn engineering notes into a standardized first draft. A fixed role, response structure, and low temperature make the resulting documents more consistent across assembly, inspection, calibration, and programming tasks. This can help engineering and production teams review a common format instead of writing every document from scratch.

However, prompt engineering cannot supply missing manufacturing facts or guarantee technical correctness. An LLM may misunderstand a task or generate unsafe details, especially when specifications are absent. The solution therefore forbids invented values, identifies missing specifications, and labels every result as a draft. Human review, approved process documents, calibrated equipment, and plant safety procedures remain authoritative.

## Security notes

- Do not commit API keys or `.env` files.
- Use environment variables or an approved secret manager.
- Rotate credentials immediately if they are exposed.
- Review `git diff` before committing or pushing.
