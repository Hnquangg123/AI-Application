"""Assignment 08: semantic search for clothing products with Azure OpenAI."""

import math
import os
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse

from openai import AzureOpenAI, OpenAI, OpenAIError
from scipy.spatial.distance import cosine


API_VERSION = "2024-07-01-preview"
ASSIGNMENT_MODEL = "text-embedding-3-small"
TOP_N = 3

# The assignment requires the sample data to be embedded directly in this file.
PRODUCTS = [
    {
        "title": "Classic Blue Jeans",
        "short_description": "Comfortable blue denim jeans with a relaxed everyday fit.",
        "price": 49.99,
        "category": "Jeans",
    },
    {
        "title": "Red Organic Cotton Hoodie",
        "short_description": "Cozy red hooded sweatshirt made from soft organic cotton.",
        "price": 39.99,
        "category": "Hoodies",
    },
    {
        "title": "Black Leather Jacket",
        "short_description": "Stylish black leather jacket with a modern slim-fit design.",
        "price": 120.00,
        "category": "Jackets",
    },
    {
        "title": "White Linen Shirt",
        "short_description": "Lightweight white linen shirt that stays breathable in warm weather.",
        "price": 44.50,
        "category": "Shirts",
    },
    {
        "title": "Floral Summer Dress",
        "short_description": "Flowing floral dress made from light fabric for sunny summer days.",
        "price": 59.95,
        "category": "Dresses",
    },
    {
        "title": "Gray Wool Sweater",
        "short_description": "Warm gray knitted wool sweater for cold autumn and winter weather.",
        "price": 69.00,
        "category": "Sweaters",
    },
    {
        "title": "Lightweight Running Shoes",
        "short_description": "Breathable athletic shoes with cushioned soles for running and exercise.",
        "price": 79.99,
        "category": "Shoes",
    },
    {
        "title": "Khaki Chino Pants",
        "short_description": "Smart casual khaki trousers with a straight fit for work or weekends.",
        "price": 54.75,
        "category": "Pants",
    },
    {
        "title": "Navy Waterproof Raincoat",
        "short_description": "Light navy raincoat with a waterproof shell and adjustable hood.",
        "price": 89.50,
        "category": "Outerwear",
    },
    {
        "title": "Green Casual T-Shirt",
        "short_description": "Soft green cotton crew-neck T-shirt for comfortable daily wear.",
        "price": 19.99,
        "category": "T-Shirts",
    },
]

# Queries are intentionally automatic; the assignment does not allow input().
DUMMY_QUERIES = [
    "warm cotton sweatshirt for cool weather",
    "light and breathable outfit for a summer day",
    "smart casual trousers for the office",
]


def load_azure_settings() -> tuple[str, str, str]:
    """Read and validate the three Azure settings required by the assignment."""
    variable_names = (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_DEPLOYMENT_NAME",
    )
    values = {name: os.getenv(name, "").strip() for name in variable_names}
    missing = [name for name, value in values.items() if not value]

    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )

    return (
        values["AZURE_OPENAI_ENDPOINT"],
        values["AZURE_OPENAI_API_KEY"],
        values["AZURE_DEPLOYMENT_NAME"],
    )


def create_embedding_client(endpoint: str, api_key: str) -> AzureOpenAI | OpenAI:
    """Create a client for either Azure or an OpenAI-compatible course gateway."""
    parsed_endpoint = urlparse(endpoint)

    # Standard Azure resource endpoints have no URL path. Some educational
    # gateways provide a path-based OpenAI-compatible base URL instead.
    if parsed_endpoint.path.strip("/"):
        return OpenAI(
            api_key=api_key,
            base_url=endpoint.rstrip("/") + "/",
        )

    return AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=endpoint,
        api_key=api_key,
    )


def get_embeddings(
    client: AzureOpenAI | OpenAI, texts: Sequence[str], deployment_name: str
) -> list[list[float]]:
    """Create embeddings for a batch of text and preserve the original order."""
    if not texts:
        return []

    response = client.embeddings.create(
        model=deployment_name,
        input=list(texts),
    )
    ordered_data = sorted(response.data, key=lambda item: item.index)
    embeddings = [item.embedding for item in ordered_data]

    if len(embeddings) != len(texts):
        raise ValueError(
            f"Expected {len(texts)} embeddings, but received {len(embeddings)}."
        )

    return embeddings


def similarity_score(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Convert cosine distance to similarity, where a higher score is better."""
    if len(vec1) != len(vec2):
        raise ValueError("Embedding vectors must have the same number of dimensions.")
    if not vec1:
        raise ValueError("Embedding vectors must not be empty.")

    score = float(1 - cosine(vec1, vec2))
    if math.isnan(score):
        raise ValueError("Cosine similarity is undefined for a zero vector.")
    return score


def rank_products(
    query_embedding: Sequence[float],
    embedded_products: Sequence[dict[str, Any]],
    top_n: int = TOP_N,
) -> list[tuple[float, dict[str, Any]]]:
    """Return the top products sorted from most to least semantically similar."""
    if top_n <= 0:
        raise ValueError("top_n must be greater than zero.")

    scored_products = []
    for product in embedded_products:
        product_embedding = product.get("embedding")
        if not isinstance(product_embedding, Sequence):
            raise ValueError(f"Product '{product['title']}' has no valid embedding.")
        score = similarity_score(query_embedding, product_embedding)
        scored_products.append((score, product))

    scored_products.sort(key=lambda item: item[0], reverse=True)
    return scored_products[:top_n]


def print_results(
    query: str, ranked_products: Sequence[tuple[float, dict[str, Any]]]
) -> None:
    """Print all product fields and the similarity score for each match."""
    print(f"\nTop {len(ranked_products)} matching products for query: '{query}'")
    print("-" * 72)

    for position, (score, product) in enumerate(ranked_products, start=1):
        print(f"{position}. Title: {product['title']}")
        print(f"   Description: {product['short_description']}")
        print(f"   Price: ${product['price']:.2f}")
        print(f"   Category: {product['category']}")
        print(f"   Similarity Score: {score:.4f}\n")


def main() -> None:
    """Embed the catalog and automatic queries, then display each ranking."""
    endpoint, api_key, deployment_name = load_azure_settings()
    client = create_embedding_client(endpoint, api_key)

    # One batched request creates embeddings for the complete product catalog.
    product_descriptions = [product["short_description"] for product in PRODUCTS]
    product_embeddings = get_embeddings(
        client, product_descriptions, deployment_name
    )
    embedded_products = [
        {**product, "embedding": embedding}
        for product, embedding in zip(PRODUCTS, product_embeddings, strict=True)
    ]

    # A second batched request creates embeddings for every automatic query.
    query_embeddings = get_embeddings(client, DUMMY_QUERIES, deployment_name)

    print(
        f"Semantic Clothing Search with {ASSIGNMENT_MODEL} "
        f"(deployment: {deployment_name})"
    )
    for query, query_embedding in zip(DUMMY_QUERIES, query_embeddings, strict=True):
        ranked_products = rank_products(query_embedding, embedded_products)
        print_results(query, ranked_products)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(f"Unable to run semantic search: {error}") from error
    except OpenAIError as error:
        raise SystemExit(
            "Azure OpenAI request failed. Check the endpoint, API key, deployment "
            f"name, and network connection. Details: {error}"
        ) from error
