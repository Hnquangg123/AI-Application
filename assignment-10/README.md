# Assignment 10 - Product Similarity Search with OpenAI and Pinecone

This project embeds a small product catalog with `text-embedding-3-small`, stores the vectors in Pinecone, and retrieves the three products most similar to an automatic sample query.

## Objective

The assignment demonstrates how to:

- Initialize the OpenAI and Pinecone Python clients.
- Create or reuse a Pinecone serverless index.
- Convert product text into 1536-dimensional embeddings.
- Upsert vectors with product metadata.
- Run a cosine-similarity query and display the top three matches.
- Handle configuration, index readiness, eventual consistency, and client cleanup.

## How it works

```text
Product title + description
          |
          v
OpenAI text-embedding-3-small
          |
          v
Pinecone product-similarity-index
          |
          v
Query: "clothing item for summer"
          |
          v
Top 3 product titles and similarity scores
```

The script uses these fixed assignment settings:

| Setting | Value |
|---|---|
| Embedding model | `text-embedding-3-small` |
| Embedding dimension | `1536` |
| Pinecone metric | `cosine` |
| Pinecone cloud/region | AWS `us-east-1` |
| Index name | `product-similarity-index` |
| Namespace | `assignment-10-products` |
| Query | `clothing item for summer` |
| Number of results | `3` |

## Product dataset

The complete sample dataset is embedded directly in `assignment_10.py`:

| ID | Title | Description |
|---|---|---|
| `prod1` | Red T-Shirt | Comfortable cotton t-shirt in bright red |
| `prod2` | Blue Jeans | Stylish denim jeans with relaxed fit |
| `prod3` | Black Leather Jacket | Genuine leather jacket with classic style |
| `prod4` | White Sneakers | Comfortable sneakers perfect for daily wear |
| `prod5` | Green Hoodie | Warm hoodie made of organic cotton |

Both the title and description are combined when generating each product embedding.

## Project files

```text
assignment-10/
|-- assignment_10.py   # Complete assignment program
|-- requirements.txt   # Python dependencies
|-- .gitignore         # Excludes secrets and local Python artifacts
`-- README.md           # Setup, usage, and verified output
```

## Installation

Python 3.10 or newer is recommended.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuration

The program reads credentials from environment variables. Do not paste real API keys into the Python file, README, or Git history.

### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your-openai-api-key"
$env:OPENAI_BASE_URL="https://aiportalapi.stu-platform.live/jpe"
$env:PINECONE_API_KEY="your-pinecone-api-key"
```

### macOS or Linux

```bash
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_BASE_URL="https://aiportalapi.stu-platform.live/jpe"
export PINECONE_API_KEY="your-pinecone-api-key"
```

The supplied URL is passed directly to the standard `OpenAI` client as its `base_url`; Azure-specific parameters and `AzureOpenAI` are not used.

## Run the assignment

```bash
python assignment_10.py
```

No manual input is required. The script automatically embeds the dataset, upserts the five records, embeds the fixed query, and requests the top three matches.

## Verified console output

The following sanitized output was captured from the final live validation run:

```text
Reusing Pinecone index 'product-similarity-index'.
Upserted 5 products into namespace 'assignment-10-products'.

Top 3 similar products for the query: 'clothing item for summer'

- Red T-Shirt (Similarity score: 0.3570)
- Green Hoodie (Similarity score: 0.3558)
- Blue Jeans (Similarity score: 0.3363)
```

Similarity scores can vary slightly if the embedding service changes its model implementation.

## Implementation notes

- Index creation is idempotent: the script reuses `product-similarity-index` when it already exists.
- Before reuse, the script verifies that the index uses 1536 dimensions and cosine similarity. It stops with a clear error rather than deleting an incompatible index.
- The dedicated namespace prevents unrelated vectors in the same index from affecting the assignment results.
- Upserted records include title and description metadata, so query results can be displayed without a second data lookup.
- The script waits for Pinecone to report all five records before querying, which handles serverless eventual consistency.
- OpenAI, Pinecone, and index clients are closed even if an API operation fails.

## Approach and challenges

The PDF example uses `AzureOpenAI`, but this submission uses the standard `OpenAI` client with an OpenAI-compatible base URL. The embedding request itself remains `client.embeddings.create(...)` with `text-embedding-3-small`.

The main operational challenges are keeping credentials out of source control and avoiding a query before Pinecone has made a recent upsert visible. Environment variables address the first issue, while bounded polling of index statistics addresses the second.

## Security

- Never commit API keys.
- `.env`, virtual environments, logs, and Python cache files are excluded by `.gitignore`.
- Rotate credentials if they are exposed in chat, screenshots, terminal recordings, or Git history.
