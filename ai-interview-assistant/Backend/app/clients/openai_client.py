from openai import OpenAI

from app.config.settings import get_settings


def get_openai_client() -> OpenAI:
    settings = get_settings()
    base_url = (settings.openai_base_url or "").strip()
    # Ignore an empty or scheme-less base URL and fall back to OpenAI's default endpoint.
    if base_url and not base_url.lower().startswith(("http://", "https://")):
        base_url = ""
    return OpenAI(
        base_url=base_url or None,
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )
