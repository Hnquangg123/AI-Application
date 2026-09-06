"""Assignment 10: retrieve the three most similar products with Pinecone."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
INDEX_NAME = "product-similarity-index"
INDEX_METRIC = "cosine"
INDEX_NAMESPACE = "assignment-10-products"
QUERY = "clothing item for summer"
TOP_K = 3
CONSISTENCY_TIMEOUT_SECONDS = 60

PRODUCTS = [
    {
        "id": "prod1",
        "title": "Red T-Shirt",
        "description": "Comfortable cotton t-shirt in bright red",
    },
    {
        "id": "prod2",
        "title": "Blue Jeans",
        "description": "Stylish denim jeans with relaxed fit",
    },
    {
        "id": "prod3",
        "title": "Black Leather Jacket",
        "description": "Genuine leather jacket with classic style",
    },
    {
        "id": "prod4",
        "title": "White Sneakers",
        "description": "Comfortable sneakers perfect for daily wear",
    },
    {
        "id": "prod5",
        "title": "Green Hoodie",
        "description": "Warm hoodie made of organic cotton",
    },
]


def load_configuration() -> tuple[str, str, str]:
    """Return required credentials and fail with a concise message if any are missing."""
    required_names = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "PINECONE_API_KEY")
    missing = [name for name in required_names if not os.getenv(name, "").strip()]
    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )

    openai_api_key = os.environ["OPENAI_API_KEY"].strip()
    openai_base_url = os.environ["OPENAI_BASE_URL"].strip().rstrip("/") + "/"
    pinecone_api_key = os.environ["PINECONE_API_KEY"].strip()
    return openai_api_key, openai_base_url, pinecone_api_key


def create_embeddings(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Create embeddings in one request and preserve the input order."""
    response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
    ordered_data = sorted(response.data, key=lambda item: item.index)
    embeddings = [item.embedding for item in ordered_data]

    if len(embeddings) != len(texts):
        raise RuntimeError(
            f"Embedding API returned {len(embeddings)} vector(s) for {len(texts)} input(s)."
        )
    if any(len(embedding) != EMBEDDING_DIMENSION for embedding in embeddings):
        raise RuntimeError(
            f"{EMBEDDING_MODEL} must return {EMBEDDING_DIMENSION}-dimensional vectors."
        )
    return embeddings


def get_field(value: Any, field: str) -> Any:
    """Read a field from either a Pinecone response object or a dictionary."""
    if isinstance(value, dict):
        return value.get(field)
    return getattr(value, field, None)


def create_or_get_index(pc: Pinecone):
    """Create the assignment index when absent and validate it before reuse."""
    if not pc.has_index(INDEX_NAME):
        print(f"Creating Pinecone index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric=INDEX_METRIC,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            timeout=120,
        )
    else:
        print(f"Reusing Pinecone index '{INDEX_NAME}'.")

    description = pc.describe_index(INDEX_NAME)
    dimension = get_field(description, "dimension")
    metric = str(get_field(description, "metric") or "").lower()
    if dimension != EMBEDDING_DIMENSION or metric != INDEX_METRIC:
        raise RuntimeError(
            f"Existing index '{INDEX_NAME}' is incompatible: expected "
            f"dimension={EMBEDDING_DIMENSION} and metric='{INDEX_METRIC}', "
            f"found dimension={dimension} and metric='{metric}'."
        )

    return pc.Index(INDEX_NAME)


def namespace_vector_count(stats: Any, namespace: str) -> int:
    """Extract a namespace vector count from a Pinecone stats response."""
    namespaces = get_field(stats, "namespaces") or {}
    namespace_stats = namespaces.get(namespace) if hasattr(namespaces, "get") else None
    if namespace_stats is None:
        return 0
    return int(get_field(namespace_stats, "vector_count") or 0)


def wait_for_upsert(index: Any, expected_count: int) -> None:
    """Wait for serverless eventual consistency before querying."""
    deadline = time.monotonic() + CONSISTENCY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        stats = index.describe_index_stats()
        if namespace_vector_count(stats, INDEX_NAMESPACE) >= expected_count:
            return
        time.sleep(1)
    raise TimeoutError(
        f"Pinecone did not report {expected_count} records in namespace "
        f"'{INDEX_NAMESPACE}' within {CONSISTENCY_TIMEOUT_SECONDS} seconds."
    )


def close_quietly(resource: Any) -> None:
    """Close an SDK resource without masking the original result or error."""
    close = getattr(resource, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def main() -> None:
    openai_api_key, openai_base_url, pinecone_api_key = load_configuration()
    openai_client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)
    pc = Pinecone(api_key=pinecone_api_key)
    index = None

    try:
        product_texts = [
            f"{product['title']}. {product['description']}" for product in PRODUCTS
        ]
        product_embeddings = create_embeddings(openai_client, product_texts)

        index = create_or_get_index(pc)
        vectors = [
            {
                "id": product["id"],
                "values": embedding,
                "metadata": {
                    "title": product["title"],
                    "description": product["description"],
                },
            }
            for product, embedding in zip(PRODUCTS, product_embeddings)
        ]
        index.upsert(vectors=vectors, namespace=INDEX_NAMESPACE)
        wait_for_upsert(index, expected_count=len(PRODUCTS))
        print(
            f"Upserted {len(PRODUCTS)} products into namespace '{INDEX_NAMESPACE}'."
        )

        query_embedding = create_embeddings(openai_client, [QUERY])[0]
        results = index.query(
            namespace=INDEX_NAMESPACE,
            vector=query_embedding,
            top_k=TOP_K,
            include_values=False,
            include_metadata=True,
        )
        matches = list(results.matches)

        if len(matches) != TOP_K:
            raise RuntimeError(f"Expected {TOP_K} matches, but Pinecone returned {len(matches)}.")

        product_ids = {product["id"] for product in PRODUCTS}
        if any(match.id not in product_ids for match in matches):
            raise RuntimeError("Pinecone returned an unexpected product ID.")
        if any(matches[i].score < matches[i + 1].score for i in range(len(matches) - 1)):
            raise RuntimeError("Pinecone results were not ordered by descending score.")

        print(f"\nTop {TOP_K} similar products for the query: '{QUERY}'\n")
        for match in matches:
            metadata = match.metadata or {}
            title = metadata.get("title", match.id)
            print(f"- {title} (Similarity score: {match.score:.4f})")
    finally:
        close_quietly(index)
        close_quietly(pc)
        close_quietly(openai_client)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
