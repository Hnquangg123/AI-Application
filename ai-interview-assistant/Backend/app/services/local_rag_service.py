"""Embedding and image extraction used by project RAG indexing.

Text and query embeddings stay local. Images are converted to accurate English
technical descriptions by the configured vision-capable chat model.
"""
from __future__ import annotations

from functools import lru_cache

from app.clients.openai_client import get_openai_client
from app.config.settings import get_settings


def _device_name() -> str:
    import torch

    preferred = get_settings().rag_device.lower()
    if preferred.startswith("cuda") and torch.cuda.is_available():
        return preferred
    return "cpu"


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(settings.rag_embedding_model, device=_device_name())


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create normalized multilingual embeddings entirely on the local machine."""
    if not texts:
        return []
    vectors = _embedding_model().encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def _validate_image_data_url(data_url: str) -> None:
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise ValueError("Expected an image data URL")


def describe_image(data_url: str, caption: str | None = None) -> str:
    """Create an English, RAG-ready technical description with GPT-4o mini."""
    _validate_image_data_url(data_url)
    settings = get_settings()
    user_prompt = (
        "Analyze this software or technical image for knowledge-base indexing. "
        "Write the result in English only. First inspect and transcribe every "
        "visible text string; the final answer must include each one verbatim, "
        "including connector labels, HTTP methods, API paths, event names, and "
        "technology names. Then identify components, directed connections, APIs, "
        "events, data stores, and data flow. For a diagram, state every visible "
        "relationship as source -> target and attach each connector label to the "
        "correct relationship. For other image types, "
        "describe only technically relevant visible information. Do not mention "
        "RAG, the indexing task, or the file name. Do not invent details that are "
        "not visible. Return concise plain text suitable for semantic search."
    )
    if caption and not caption.strip().lower().endswith(
        (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
    ):
        user_prompt += f" User-provided context: {caption.strip()}"

    response = get_openai_client().chat.completions.create(
        model=settings.rag_vision_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You accurately analyze technical images and architecture "
                    "diagrams. Always answer in English."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    },
                ],
            },
        ],
        max_tokens=700,
    )
    description = (response.choices[0].message.content or "").strip()
    if not description:
        raise ValueError("The vision model returned an empty image description")
    return description
