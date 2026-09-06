"""Assignment 11: a LangChain agent for weather and web-search queries."""

from __future__ import annotations

import json
import os
import warnings
from datetime import date
from typing import Any
from urllib.parse import urlparse

# The assignment intentionally uses this wrapper while its standalone successor
# is still being developed. Keep the console demo focused on the agent output.
warnings.filterwarnings(
    "ignore",
    message=r"`langchain-community` is being sunset.*",
    category=DeprecationWarning,
)

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch


REQUIRED_ENV_VARS = (
    "OPENAI_API_KEY",
    "OPENAI_ENDPOINT",
    "OPENWEATHERMAP_API_KEY",
    "TAVILY_API_KEY",
)

MOCK_QUESTIONS = [
    "What's the weather in Hanoi?",
    "Tell me about the latest news in AI.",
    "Who won the last World Cup?",
    "exit",
]


def validate_environment() -> None:
    """Raise a clear error when one or more required settings are absent."""
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variables: {names}")


def normalize_openai_base_url(endpoint: str) -> str:
    """Validate an OpenAI-compatible endpoint and add `/v1` when needed."""
    normalized = endpoint.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("OPENAI_ENDPOINT must be a valid HTTP or HTTPS URL.")

    if parsed.path.rstrip("/").endswith(("/v1", "/v2")):
        return normalized
    return f"{normalized}/v1"


def build_tools() -> list[Any]:
    """Create the OpenWeather and Tavily tools used by the agent."""
    weather_client = OpenWeatherMapAPIWrapper()
    tavily_client = TavilySearch(
        max_results=3,
        topic="general",
        include_answer=True,
    )

    @tool
    def get_weather(city: str) -> str:
        """Get the current weather for a city using OpenWeather."""
        print(f"[Tool] get_weather called for: {city}")
        try:
            return weather_client.run(city)
        except Exception as error:  # Keep the conversation alive after API failures.
            return f"OpenWeather request failed: {type(error).__name__}."

    @tool
    def search_web(query: str) -> str:
        """Search the web for current news or factual information using Tavily."""
        print(f"[Tool] search_web called for: {query}")
        try:
            result = tavily_client.invoke({"query": query})
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as error:  # Keep the conversation alive after API failures.
            return f"Tavily search failed: {type(error).__name__}."

    return [get_weather, search_web]


def build_agent() -> Any:
    """Initialize GPT-4o-mini and the LangChain tool-calling agent."""
    endpoint = normalize_openai_base_url(os.environ["OPENAI_ENDPOINT"])
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    model = ChatOpenAI(
        model=model_name,
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=endpoint,
        temperature=0,
        timeout=60,
        max_retries=2,
    )

    system_prompt = f"""
You are a helpful weather and web-search assistant. Today's date is {date.today().isoformat()}.

Tool-routing rules:
- For current weather questions, you must call get_weather.
- For current news, recent events, or factual general-knowledge questions, you must call search_web.
- Do not answer these questions from memory when an appropriate tool is available.
- Never invent a tool result. If a tool reports an error, explain it briefly to the user.
- Give concise, user-friendly answers. For web searches, include the source URLs returned by Tavily.
""".strip()

    return create_agent(
        model=model,
        tools=build_tools(),
        system_prompt=system_prompt,
    )


def message_text(content: Any) -> str:
    """Convert the final model content into readable console text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        if text_parts:
            return "\n".join(text_parts)
    return str(content)


def run_conversation(agent: Any, questions: list[str] | None = None) -> None:
    """Run the required automatic conversation while retaining chat history."""
    print("Welcome to the AI assistant. Type 'exit' to stop.")
    messages: list[Any] = []

    for user_input in questions or MOCK_QUESTIONS:
        print(f"\nUser: {user_input}")
        if user_input.strip().lower() == "exit":
            print("Goodbye!")
            break

        user_message = {"role": "user", "content": user_input}
        turn_messages = [*messages, user_message]

        try:
            response = agent.invoke({"messages": turn_messages})
            messages = response["messages"]
            print(f"AI: {message_text(messages[-1].content)}")
        except Exception as error:
            error_message = (
                f"I could not complete this request because of "
                f"{type(error).__name__}. Please check the API configuration and try again."
            )
            print(f"AI: {error_message}")
            messages.extend(
                [
                    user_message,
                    {"role": "assistant", "content": error_message},
                ]
            )


def main() -> int:
    """Load configuration, create the agent, and run the assignment demo."""
    load_dotenv()
    try:
        validate_environment()
        agent = build_agent()
    except (RuntimeError, ValueError) as error:
        print(f"Configuration error: {error}")
        return 1

    run_conversation(agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
