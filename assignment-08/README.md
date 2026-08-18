# Assignment 08 - Semantic Search for Clothing Products

This project implements a small semantic search engine for an online clothing catalog. It uses Azure OpenAI's `text-embedding-3-small` deployment to convert product descriptions and search queries into vectors, then ranks products using cosine similarity.

## Features

- Ten clothing products stored directly in the Python script
- Three automatic sample queries (no interactive `input()` call)
- Batched embedding requests for products and queries
- Cosine-similarity ranking with the top three results per query
- Clear output containing title, description, price, category, and similarity score

## Project structure

```text
assignment-08/
|-- semantic_search.py
`-- README.md
```

`semantic_search.py` is the only Python source file, as required by the assignment.

## Requirements

- Python 3.10 or newer
- An Azure OpenAI-compatible endpoint and API key
- An embedding deployment named `text-embedding-3-small`
- The `openai` and `scipy` Python packages

## Installation

Create and activate a virtual environment, then install the dependencies.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install openai scipy
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install openai scipy
```

## Azure OpenAI configuration

The script reads configuration from environment variables. Replace the placeholders with values from your Azure OpenAI-compatible service.

### Windows PowerShell

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://your-resource-endpoint"
$env:AZURE_OPENAI_API_KEY = "your-api-key"
$env:AZURE_DEPLOYMENT_NAME = "text-embedding-3-small"
```

### macOS or Linux

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource-endpoint"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_DEPLOYMENT_NAME="text-embedding-3-small"
```

Do not place a real API key in `semantic_search.py`, `README.md`, or a Git commit.

## Usage

Run the script after activating the virtual environment and setting the three environment variables:

```bash
python semantic_search.py
```

The script automatically searches for these three descriptions:

1. `warm cotton sweatshirt for cool weather`
2. `light and breathable outfit for a summer day`
3. `smart casual trousers for the office`

The output follows this format. This example comes from a successful live run; exact scores may vary if the service updates the model:

```text
Top 3 matching products for query: 'warm cotton sweatshirt for cool weather'
------------------------------------------------------------------------
1. Title: Gray Wool Sweater
   Description: Warm gray knitted wool sweater for cold autumn and winter weather.
   Price: $69.00
   Category: Sweaters
   Similarity Score: 0.6214
```

## How the semantic search works

1. The script creates an `AzureOpenAI` client with API version `2024-07-01-preview` for a standard Azure resource endpoint. A path-based institutional gateway uses the official `OpenAI` client's compatible `base_url` mode.
2. It sends all ten product descriptions in one embedding request.
3. It sends all three dummy queries in a second embedding request.
4. The service returns one numeric embedding vector for each text.
5. Each query vector is compared with every product vector.
6. Products are sorted by similarity, and the three highest-scoring products are printed.

Embeddings capture meaning rather than requiring exact keyword matches. For example, a query about a "sweatshirt" can still match a product described as a "hoodie."

## Cosine similarity

Cosine similarity measures the angle between two vectors:

```text
cosine_similarity(A, B) = (A . B) / (||A|| * ||B||)
```

SciPy's `cosine()` function returns cosine **distance**, so the script converts it to similarity:

```python
similarity = 1 - cosine(query_embedding, product_embedding)
```

A higher score means the query and product description are more semantically related. The script sorts scores in descending order.

## Challenges and limitations

- The program requires a working network connection and valid Azure OpenAI credentials.
- Some educational gateways expose an OpenAI-compatible URL instead of Azure's deployment-style URL; the script detects path-based gateway endpoints automatically.
- Product and query embeddings are regenerated every run; they are not cached or stored in a database.
- The catalog is a small in-memory sample rather than a production product database.
- Search uses only `short_description`; title, category, price, inventory, and user preferences do not affect ranking.
- Semantic relevance depends on the embedding model and the quality of the product descriptions.
- Cosine ranking alone does not apply business rules such as price ranges or stock availability.

For a larger production catalog, product embeddings should be created once, stored in a vector database, and updated only when product information changes.

## Security notes

- Keep API keys in environment variables or a managed secret store.
- Never commit credentials to Git.
- Rotate a key immediately if it is accidentally exposed.
