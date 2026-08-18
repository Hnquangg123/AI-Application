# Assignment 06 - Logistics Delay Reason Classification

## Description

This project classifies unstructured logistics, delivery, and maintenance logs into a fixed set of operational delay reasons. It uses a two-stage NLP pipeline:

1. A deterministic keyword-based pre-classifier assigns an initial category.
2. Azure OpenAI confirms or corrects that category using the full log context.

The hybrid design provides an auditable baseline while allowing an AI model to handle wording that simple rules may miss.

## Features

- Processes the ten assignment logs automatically.
- Uses a fixed taxonomy of eight operational categories.
- Preserves both heuristic and Azure-refined predictions.
- Uses temperature `0` for consistent classification.
- Strictly rejects model output outside the allowed taxonomy.
- Continues processing after an individual API or validation failure.
- Prints a readable results table and success/failure summary.
- Does not use manual console input.
- Explains how direct classification differs from retrieval-based pipelines.

## Project Structure

```text
assignment-06/
|-- assignment06_delay_classifier.py
`-- README.md
```

The complete implementation and all ten sample logs are contained in the single Python file required by the assignment.

## Delay Categories

Every successful prediction is one of these values:

| Category | Typical examples |
|---|---|
| Traffic | Congestion, construction, road accidents |
| Customer Issue | Unavailable customer, unreachable customer, incorrect address |
| Vehicle Issue | Engine failure or vehicle breakdown |
| Weather | Rainstorms, snow, floods, or other weather disruption |
| Sorting/Labeling Error | Missing labels, barcode problems, sorting issues |
| Human Error | Wrong turns, unnecessary rerouting, driver mistakes |
| Technical System Failure | System glitches or check-in technology failures |
| Other | No delay or no matching operational cause |

## Requirements

- Python 3.9 or newer
- `openai` Python package
- An Azure OpenAI resource with a compatible chat-model deployment
- Azure endpoint, API key, and deployment name

## Installation

### 1. Clone or download the repository

```bash
git clone <your-repository-url>
cd assignment-06
```

### 2. Create a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Bash or zsh:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install the dependency

```bash
python -m pip install --upgrade pip
python -m pip install openai
```

## Azure Configuration

Credentials are read from environment variables and are not stored in the source code.

PowerShell:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com/"
$env:AZURE_OPENAI_API_KEY = "YOUR-API-KEY"
$env:AZURE_DEPLOYMENT_NAME = "YOUR-DEPLOYMENT-NAME"
```

Bash or zsh:

```bash
export AZURE_OPENAI_ENDPOINT="https://YOUR-RESOURCE.openai.azure.com/"
export AZURE_OPENAI_API_KEY="YOUR-API-KEY"
export AZURE_DEPLOYMENT_NAME="YOUR-DEPLOYMENT-NAME"
```

The implementation uses Azure API version `2024-07-01-preview` to align with the assignment example.

## Usage

Run the classifier from the project directory:

```bash
python assignment06_delay_classifier.py
```

The program loads all ten sample logs, performs both classification stages, prints the results table, and displays a short comparison with retrieval-based pipelines.

If any required environment variable is missing, the application exits clearly rather than pretending that heuristic-only output came from Azure.

## Classification Flow

```text
Free-text log
    |
    v
Keyword pre-classifier
    |
    v
Initial category
    |
    v
Azure OpenAI refinement
    |
    v
Validated final category
```

### Heuristic stage

`initial_classify()` normalizes the input and checks ordered keyword groups. For example, `road accident` maps to Traffic and `engine failed` maps to Vehicle Issue. Text with no match maps to Other.

### Azure refinement stage

The model receives the log, initial prediction, and complete category list. The system instruction treats the log as untrusted data and requires exactly one category without explanation. The returned text is normalized and checked against the taxonomy before it is accepted.

## Representative Results

Azure credentials were not configured when this submission was prepared, so the following table is representative rather than captured from a live deployment.

| ID | Log entry | Predicted category |
|---:|---|---|
| 1 | Driver reported heavy traffic on highway due to construction | Traffic |
| 2 | Package not accepted, customer unavailable at given time | Customer Issue |
| 3 | Vehicle engine failed during route, replacement dispatched | Vehicle Issue |
| 4 | Unexpected rainstorm delayed loading at warehouse | Weather |
| 5 | Sorting label missing, required manual barcode scan | Sorting/Labeling Error |
| 6 | Driver took a wrong turn and had to reroute | Human Error |
| 7 | No issue reported, arrived on time | Other |
| 8 | Address was incorrect, customer unreachable | Customer Issue |
| 9 | System glitch during check-in at loading dock | Technical System Failure |
| 10 | Road accident caused a long halt near delivery point | Traffic |

Actual Azure responses must still pass the same strict category validation.

## Classification vs. Retrieval-Based Pipelines

This solution directly maps each short log to a category using rules followed by an LLM. It does not search an external knowledge base. This approach fits high-volume routing, dashboards, and operational reporting when the taxonomy is stable and each log contains enough information to decide the label.

A retrieval-based pipeline first searches a collection such as maintenance manuals, company policies, route history, or previous incidents. It then uses the retrieved evidence to answer or classify. Retrieval is a better fit when the decision depends on detailed reference material, traceable supporting evidence, or frequently changing operational knowledge.

## Error Handling

The program handles:

- Missing Azure environment variables
- Azure client initialization errors
- API failures for individual logs
- Empty model responses
- Malformed response structures
- Categories outside the allowed taxonomy
- Empty log text or invalid initial labels

An individual log failure is recorded as an error and does not prevent later logs from being processed.

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | All ten logs were classified successfully |
| `1` | Configuration or Azure client initialization failed |
| `2` | Processing completed with one or more failed logs |

## Privacy and Security

- The API key is read from an environment variable and is never printed.
- Log text is sent to the configured Azure OpenAI resource for refinement.
- Logs should be reviewed for sensitive operational or personal data before production use.
- The system prompt tells the model to treat log content as data rather than instructions.

## Troubleshooting

### Missing environment variables

Set all three Azure variables in the same terminal session used to run the script.

### Authentication or endpoint errors

Confirm that the endpoint belongs to the Azure OpenAI resource, the key is active, and the deployment name matches an existing model deployment.

### Model returns extra explanation

The program intentionally rejects responses that are not exactly one allowed category. Run the request again or review the deployed model's instruction-following behavior.

### Some logs fail but later logs continue

This is expected batch behavior. Review the error printed beneath the failed table row and the final summary.

## Limitations

- The keyword rules are intentionally small and designed for the supplied examples.
- Each log uses a separate Azure request, which favors clarity over minimum request count.
- Classification quality depends on the deployed model and prompt adherence.
- The representative output table is not a substitute for a live test using the submitter's Azure deployment.
- This project does not use embeddings, a vector database, or retrieval-augmented generation.

## Project Status

The Assignment 06 implementation is complete. Syntax, heuristic classifications, prompt construction, strict label validation, batch continuation, and configuration errors are verified locally with a fake Azure client. A live Azure run remains pending because credentials are not configured in this environment.
