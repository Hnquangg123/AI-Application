"""Assignment 09: Laptop consultant chatbot using Azure OpenAI and ChromaDB."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.errors import ChromaError
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    AzureOpenAI,
    OpenAIError,
)

API_VERSION = "2023-05-15"
COLLECTION_NAME = "laptops"

LAPTOPS = (
    {
        "id": "1",
        "name": "Gaming Beast Pro",
        "description": (
            "A high-end gaming laptop with RTX 4080, 32GB RAM, and 1TB SSD. "
            "Perfect for hardcore gaming."
        ),
        "tags": "gaming, high-performance, windows",
    },
    {
        "id": "2",
        "name": "Business Ultrabook X1",
        "description": (
            "A lightweight business laptop with Intel i7, 16GB RAM, and long "
            "battery life. Great for productivity."
        ),
        "tags": "business, ultrabook, lightweight",
    },
    {
        "id": "3",
        "name": "Student Basic",
        "description": (
            "Affordable laptop with 8GB RAM, 256GB SSD, and a reliable battery. "
            "Ideal for students and general use."
        ),
        "tags": "student, budget, general",
    },
)

USER_QUERIES = (
    "I want a lightweight laptop with long battery life for business trips.",
    "I need a laptop for gaming with the best graphics card available.",
    "Looking for a budget laptop suitable for student tasks and general browsing.",
)


class ConfigurationError(ValueError):
    """Raised when required environment variables have not been configured."""


@dataclass(frozen=True)
class AppConfig:
    """Environment-based configuration for the two Azure OpenAI clients."""

    embedding_api_key: str
    embedding_endpoint: str
    embedding_model: str
    llm_api_key: str
    llm_endpoint: str
    llm_model: str

    @classmethod
    def from_environment(cls) -> AppConfig:
        variable_names = {
            "embedding_api_key": "AZURE_OPENAI_EMBEDDING_API_KEY",
            "embedding_endpoint": "AZURE_OPENAI_EMBEDDING_ENDPOINT",
            "embedding_model": "AZURE_OPENAI_EMBED_MODEL",
            "llm_api_key": "AZURE_OPENAI_LLM_API_KEY",
            "llm_endpoint": "AZURE_OPENAI_LLM_ENDPOINT",
            "llm_model": "AZURE_OPENAI_LLM_MODEL",
        }
        values = {
            field: os.getenv(variable, "").strip()
            for field, variable in variable_names.items()
        }
        missing = [
            variable for field, variable in variable_names.items() if not values[field]
        ]
        if missing:
            raise ConfigurationError(
                "Missing required environment variables: " + ", ".join(missing)
            )
        return cls(**values)


def create_clients(config: AppConfig) -> tuple[AzureOpenAI, AzureOpenAI]:
    """Create separate embedding and chat clients as required by the assignment."""

    embedding_client = AzureOpenAI(
        api_key=config.embedding_api_key,
        azure_endpoint=config.embedding_endpoint,
        api_version=API_VERSION,
    )
    llm_client = AzureOpenAI(
        api_key=config.llm_api_key,
        azure_endpoint=config.llm_endpoint,
        api_version=API_VERSION,
    )
    return embedding_client, llm_client


def get_embedding(text: str, client: Any, model: str) -> list[float]:
    """Return an embedding vector for a piece of text."""

    response = client.embeddings.create(input=text, model=model)
    return response.data[0].embedding


def create_laptop_collection(embedding_client: Any, model: str) -> Any:
    """Create and populate an in-memory ChromaDB laptop collection."""

    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    embeddings = [
        get_embedding(laptop["description"], embedding_client, model)
        for laptop in LAPTOPS
    ]
    collection.upsert(
        ids=[laptop["id"] for laptop in LAPTOPS],
        documents=[laptop["description"] for laptop in LAPTOPS],
        embeddings=embeddings,
        metadatas=[
            {"name": laptop["name"], "tags": laptop["tags"]} for laptop in LAPTOPS
        ],
    )
    return collection


def retrieve_laptops(
    user_input: str,
    collection: Any,
    embedding_client: Any,
    model: str,
    n_results: int = 3,
) -> dict[str, Any]:
    """Retrieve the laptops most relevant to a user's requirements."""

    query_embedding = get_embedding(user_input, embedding_client, model)
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, len(LAPTOPS)),
        include=["documents", "metadatas"],
    )


def build_context(results: dict[str, Any], n_context: int = 3) -> str:
    """Convert ChromaDB query results into grounded context for the chat model."""

    document_batches = results.get("documents") or []
    metadata_batches = results.get("metadatas") or []
    if not document_batches or not metadata_batches:
        raise RuntimeError("ChromaDB returned no laptop results.")

    documents = document_batches[0]
    metadatas = metadata_batches[0]
    context_parts = []
    for document, metadata in list(zip(documents, metadatas))[:n_context]:
        context_parts.append(
            "\n".join(
                (
                    f"Name: {metadata['name']}",
                    f"Description: {document}",
                    f"Tags: {metadata['tags']}",
                )
            )
        )

    if not context_parts:
        raise RuntimeError("ChromaDB returned no usable laptop results.")
    return "\n\n".join(context_parts)


def ask_llm(context: str, user_input: str, client: Any, model: str) -> str:
    """Ask the chat model for a recommendation grounded in retrieved laptops."""

    system_prompt = (
        "You are a helpful assistant specializing in laptop recommendations. "
        "Use only the laptops in the provided context. Recommend the best option "
        "or options for the user's needs and explain the reasons clearly. Do not "
        "invent products or specifications that are not present in the context."
    )
    user_prompt = (
        f"User requirements: {user_input}\n\n"
        f"Context (top relevant laptops):\n{context}\n\n"
        "Based on the context, which laptop or laptops would you recommend and why?"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    recommendation = response.choices[0].message.content
    if not recommendation:
        raise RuntimeError("The chat model returned an empty recommendation.")
    return recommendation


def run_recommendations(
    config: AppConfig, embedding_client: Any, llm_client: Any
) -> None:
    """Run the three automated recommendation scenarios from the assignment."""

    collection = create_laptop_collection(
        embedding_client=embedding_client,
        model=config.embedding_model,
    )

    for user_input in USER_QUERIES:
        print("=" * 60)
        print(f"User input: {user_input}")
        results = retrieve_laptops(
            user_input=user_input,
            collection=collection,
            embedding_client=embedding_client,
            model=config.embedding_model,
        )
        context = build_context(results)
        recommendation = ask_llm(
            context=context,
            user_input=user_input,
            client=llm_client,
            model=config.llm_model,
        )
        print("\nLLM Recommendation:\n")
        print(recommendation)
        print("=" * 60, end="\n\n")


def main() -> int:
    """Load configuration, run all mock queries, and return a process exit code."""

    try:
        config = AppConfig.from_environment()
        embedding_client, llm_client = create_clients(config)
        run_recommendations(config, embedding_client, llm_client)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except AuthenticationError:
        print(
            "Authentication failed. Check the Azure OpenAI API key variables.",
            file=sys.stderr,
        )
        return 3
    except APIConnectionError:
        print(
            "Could not connect to the Azure OpenAI endpoint. Check the endpoint "
            "variables and network connection.",
            file=sys.stderr,
        )
        return 4
    except APIStatusError as exc:
        print(
            f"Azure OpenAI returned HTTP {exc.status_code}. Check the endpoint, "
            "deployment names, and API version.",
            file=sys.stderr,
        )
        return 5
    except OpenAIError:
        print(
            "Azure OpenAI request failed. Check the configured resource and models.",
            file=sys.stderr,
        )
        return 6
    except KeyboardInterrupt:
        print("\nChatbot stopped by the user.", file=sys.stderr)
        return 130
    except (
        ChromaError,
        IndexError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"Application error: {exc}", file=sys.stderr)
        return 1

    print("Completed all three laptop recommendation queries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
