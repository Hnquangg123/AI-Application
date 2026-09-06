"""Assignment 12: classify satellite images as Cloudy or Clear with GPT-4o-mini."""

from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


IMAGE_URLS = [
    "https://eoimages.gsfc.nasa.gov/images/imagerecords/149000/149677/"
    "southernhemisphere_tmo_2022093_lrg.jpg",
    "https://eoimages.gsfc.nasa.gov/images/imagerecords/35000/35518/"
    "roan_tmo_2008269_lrg.jpg",
    "https://eoimages.gsfc.nasa.gov/images/imagerecords/145000/145628/"
    "iss059e036413_lrg.jpg",
]

SYSTEM_PROMPT = """
You classify satellite and Earth-observation images by visible cloud cover.

Classification rules:
- Return "Cloudy" when clouds visibly cover any meaningful part of the scene.
- Return "Clear" only when the scene is essentially cloud-free.
- Do not mistake snow, sea ice, smoke, haze, or bright terrain for clouds.
- Confidence must be a number from 0 to 100 representing your confidence in the label.
- Return only the fields required by the response schema and no explanation.
""".strip()


class CloudDetectionResult(BaseModel):
    """Structured result returned for one satellite image."""

    label: Literal["Cloudy", "Clear"] = Field(
        description="Cloud-cover classification for the image."
    )
    confidence: float = Field(
        ge=0,
        le=100,
        description="Self-reported confidence percentage from 0 to 100.",
    )


def load_configuration() -> tuple[str, str, str]:
    """Load and validate the gateway settings without exposing credentials."""
    missing = [
        name
        for name in ("OPENAI_API_KEY", "OPENAI_ENDPOINT")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    endpoint = os.environ["OPENAI_ENDPOINT"].strip()
    parsed_endpoint = urlparse(endpoint)
    if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.netloc:
        raise ValueError("OPENAI_ENDPOINT must be a valid HTTP or HTTPS URL.")

    api_key = os.environ["OPENAI_API_KEY"]
    model_name = os.getenv("OPENAI_MODEL", "GPT-4o-mini").strip()
    if not model_name:
        raise ValueError("OPENAI_MODEL cannot be empty.")

    return api_key, endpoint, model_name


def build_classifier(api_key: str, endpoint: str, model_name: str) -> Any:
    """Create a structured-output classifier using the exact gateway base URL."""
    model = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=endpoint,
        temperature=0,
        timeout=60,
        max_retries=2,
    )
    return model.with_structured_output(
        CloudDetectionResult,
        method="json_schema",
    )


def classify_image(classifier: Any, image_url: str) -> CloudDetectionResult:
    """Classify one remote image through a multimodal chat message."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Classify this scene as Cloudy or Clear and report confidence.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url, "detail": "low"},
                },
            ],
        },
    ]

    result = classifier.invoke(messages)
    if not isinstance(result, CloudDetectionResult):
        raise TypeError("The model returned an unexpected response type.")
    return result


def process_images(classifier: Any, image_urls: list[str] | None = None) -> int:
    """Process the automatic image list and return the number of failures."""
    urls = IMAGE_URLS if image_urls is None else image_urls
    failures = 0

    print(f"Satellite Cloud Detection - processing {len(urls)} images")
    for index, image_url in enumerate(urls, start=1):
        print(f"\n[{index}/{len(urls)}] Image: {image_url}")
        try:
            result = classify_image(classifier, image_url)
            print(f"Prediction: {result.label}")
            print(f"Confidence: {result.confidence:.1f}%")
        except Exception as error:
            failures += 1
            print(
                "Error: classification failed "
                f"({type(error).__name__}). Check the API configuration and network."
            )

    print(f"\nCompleted: {len(urls) - failures} succeeded, {failures} failed.")
    return failures


def main() -> int:
    """Load configuration and run the required three-image demonstration."""
    load_dotenv()
    try:
        api_key, endpoint, model_name = load_configuration()
        classifier = build_classifier(api_key, endpoint, model_name)
    except (RuntimeError, ValueError) as error:
        print(f"Configuration error: {error}")
        return 1

    return 1 if process_images(classifier) else 0


if __name__ == "__main__":
    raise SystemExit(main())
