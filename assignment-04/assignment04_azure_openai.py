"""Batch travel-itinerary generation with Azure OpenAI function calling.

This assignment demonstrates:
- Azure OpenAI Chat Completions with a function tool
- Sequential batch processing
- Exponential-backoff retries for transient API failures
- Per-item exception handling and structured result collection
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    AzureOpenAI,
    InternalServerError,
    RateLimitError,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)


API_VERSION = "2024-07-01-preview"
TOOL_NAME = "generate_itinerary"
LOGGER = logging.getLogger(__name__)

REQUIRED_ENVIRONMENT_VARIABLES = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_DEPLOYMENT_NAME",
)

ITINERARY_TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "Create a practical day-by-day travel itinerary for a destination "
            "and a specified number of days."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Travel destination city or country.",
                },
                "duration_days": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Number of days covered by the itinerary.",
                },
                "summary": {
                    "type": "string",
                    "description": "A short overview of the itinerary.",
                },
                "daily_plan": {
                    "type": "array",
                    "description": "One plan entry for each day of the trip.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day": {"type": "integer", "minimum": 1},
                            "title": {"type": "string"},
                            "activities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            },
                        },
                        "required": ["day", "title", "activities"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [
                "destination",
                "duration_days",
                "summary",
                "daily_plan",
            ],
            "additionalProperties": False,
        },
    },
}

BATCH_INPUTS = [
    {
        "prompt": "Plan a balanced travel itinerary with major sights and local culture.",
        "destination": "Paris",
        "days": 3,
    },
    {
        "prompt": "Plan a balanced travel itinerary with major sights and local culture.",
        "destination": "Tokyo",
        "days": 5,
    },
    {
        "prompt": "Plan a balanced travel itinerary with major sights and local culture.",
        "destination": "New York",
        "days": 4,
    },
]


def configure_logging() -> None:
    """Configure concise console logging for retries and per-item errors."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def load_configuration() -> dict[str, str]:
    """Load required Azure settings, failing without revealing secret values."""
    missing = [
        name for name in REQUIRED_ENVIRONMENT_VARIABLES if not os.getenv(name, "").strip()
    ]
    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )

    return {name: os.environ[name].strip() for name in REQUIRED_ENVIRONMENT_VARIABLES}


def create_client(configuration: dict[str, str]) -> AzureOpenAI:
    """Create an authenticated Azure OpenAI client."""
    return AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=configuration["AZURE_OPENAI_ENDPOINT"],
        api_key=configuration["AZURE_OPENAI_API_KEY"],
    )


def _validate_batch_item(item: dict[str, Any]) -> None:
    """Validate one input before making a billable API request."""
    if not isinstance(item, dict):
        raise TypeError("Each batch item must be a dictionary.")

    for field in ("prompt", "destination"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError(f"Input field '{field}' must be a non-empty string.")

    days = item.get("days")
    if isinstance(days, bool) or not isinstance(days, int) or days < 1:
        raise ValueError("Input field 'days' must be a positive integer.")


def _validate_itinerary(payload: Any, expected_days: int) -> dict[str, Any]:
    """Validate model-generated tool arguments before accepting the result."""
    if not isinstance(payload, dict):
        raise ValueError("Tool arguments must decode to a JSON object.")

    for field in ("destination", "summary"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"Tool output field '{field}' must be a non-empty string.")

    duration_days = payload.get("duration_days")
    if isinstance(duration_days, bool) or duration_days != expected_days:
        raise ValueError(
            f"Tool output duration_days must equal the requested {expected_days} days."
        )

    daily_plan = payload.get("daily_plan")
    if not isinstance(daily_plan, list) or len(daily_plan) != expected_days:
        raise ValueError(
            f"Tool output daily_plan must contain exactly {expected_days} entries."
        )

    expected_day_numbers = list(range(1, expected_days + 1))
    actual_day_numbers: list[int] = []
    for position, plan in enumerate(daily_plan, start=1):
        if not isinstance(plan, dict):
            raise ValueError(f"Daily plan entry {position} must be an object.")

        day = plan.get("day")
        if isinstance(day, bool) or not isinstance(day, int):
            raise ValueError(f"Daily plan entry {position} has an invalid day number.")
        actual_day_numbers.append(day)

        if not isinstance(plan.get("title"), str) or not plan["title"].strip():
            raise ValueError(f"Daily plan entry {position} needs a non-empty title.")

        activities = plan.get("activities")
        if (
            not isinstance(activities, list)
            or not activities
            or any(not isinstance(activity, str) or not activity.strip() for activity in activities)
        ):
            raise ValueError(
                f"Daily plan entry {position} needs one or more text activities."
            )

    if actual_day_numbers != expected_day_numbers:
        raise ValueError(
            "Daily plan day numbers must be consecutive and start at 1."
        )

    return payload


def _extract_tool_arguments(response: Any, expected_days: int) -> dict[str, Any]:
    """Extract and validate arguments from the named function tool call."""
    if not getattr(response, "choices", None):
        raise ValueError("Azure OpenAI returned no completion choices.")

    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        raise ValueError("Azure OpenAI returned no function tool call.")

    matching_calls = [
        tool_call
        for tool_call in tool_calls
        if getattr(tool_call, "type", None) == "function"
        and getattr(tool_call.function, "name", None) == TOOL_NAME
    ]
    if len(matching_calls) != 1:
        raise ValueError(
            f"Expected exactly one '{TOOL_NAME}' tool call; received {len(matching_calls)}."
        )

    raw_arguments = matching_calls[0].function.arguments
    try:
        payload = json.loads(raw_arguments)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Function tool arguments were not valid JSON.") from exc

    return _validate_itinerary(payload, expected_days)


@retry(
    retry=retry_if_exception_type(
        (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
    ),
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(LOGGER, logging.WARNING),
    reraise=True,
)
def call_openai_function(client: AzureOpenAI, item: dict[str, Any]) -> dict[str, Any]:
    """Request and validate one itinerary, retrying only transient API failures."""
    _validate_batch_item(item)

    deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "").strip()
    if not deployment_name:
        raise RuntimeError("AZURE_DEPLOYMENT_NAME is not configured.")

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a practical travel planner. Return the requested itinerary "
                    "by calling the generate_itinerary function exactly once."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{item['prompt']}\n"
                    f"Destination: {item['destination']}\n"
                    f"Duration: {item['days']} days"
                ),
            },
        ],
        tools=[ITINERARY_TOOL],
        tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
        temperature=0.3,
    )
    return _extract_tool_arguments(response, item["days"])


def batch_process(
    client: AzureOpenAI, inputs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Process every input and preserve a success or error record for each one."""
    results: list[dict[str, Any]] = []

    for index, item in enumerate(inputs, start=1):
        destination = item.get("destination", f"item {index}") if isinstance(item, dict) else f"item {index}"
        LOGGER.info("Processing %s (%d of %d)", destination, index, len(inputs))

        try:
            itinerary = call_openai_function(client, item)
            results.append(
                {
                    "input": {
                        "destination": item["destination"],
                        "days": item["days"],
                    },
                    "status": "success",
                    "output": itinerary,
                }
            )
        except Exception as exc:  # Continue the batch after any per-item failure.
            LOGGER.error("Could not process %s: %s", destination, exc)
            results.append(
                {
                    "input": {
                        "destination": destination,
                        "days": item.get("days") if isinstance(item, dict) else None,
                    },
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    return results


def print_results(results: list[dict[str, Any]]) -> None:
    """Print collected results and a final batch summary."""
    print("\nBATCH RESULTS")
    print("=" * 60)
    for index, result in enumerate(results, start=1):
        print(f"Result {index}:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("-" * 60)

    success_count = sum(result["status"] == "success" for result in results)
    failure_count = len(results) - success_count
    print(
        f"Summary: {len(results)} processed, "
        f"{success_count} succeeded, {failure_count} failed."
    )


def main() -> int:
    """Validate configuration, process the sample batch, and return a status code."""
    configure_logging()

    try:
        configuration = load_configuration()
    except RuntimeError as exc:
        LOGGER.error("Configuration error: %s", exc)
        LOGGER.error("Set the required variables and run the script again.")
        return 1

    client = create_client(configuration)
    results = batch_process(client, BATCH_INPUTS)
    print_results(results)

    return 0 if all(result["status"] == "success" for result in results) else 2


if __name__ == "__main__":
    sys.exit(main())
