from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str | None = None
    openai_model_chat: str = "gpt-4o-mini"
    openai_chat_api: Literal["auto", "responses", "chat_completions"] = "auto"
    openai_timeout_seconds: float = 30.0
    rag_embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_embedding_dimensions: int = 384
    rag_vision_model: str = "gpt-4o-mini"
    rag_device: str = "cpu"

    database_url: str = (
        "postgresql+psycopg://interview_app:interview_dev_password@localhost:5432/"
        "interview_assistant"
    )
    database_echo: bool = False
    frontend_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Workshop 3 - local Text-to-Speech (Microsoft SpeechT5)
    tts_enabled: bool = True
    tts_model_id: str = "microsoft/speecht5_tts"
    tts_vocoder_id: str = "microsoft/speecht5_hifigan"
    tts_device: str = "cpu"              # "cuda:0" (NVIDIA GPU) or "mps" (Apple Silicon / M1)
    tts_speaker_index: int = 7306        # seed for the generated speaker embedding (the "voice")
    tts_speaker_embedding_path: str | None = None  # optional .npy/.pt x-vector for a real voice
    tts_normalize: bool = True           # peak-normalise so the audio is as loud as possible
    tts_gain: float = 1.0                # extra volume multiplier (raise for louder; may clip)
    tts_cache_dir: str = "data/tts"
    tts_warm_up_on_start: bool = False

    app_env: str = "dev"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # BaseSettings resolves required values from environment variables at runtime.
    return Settings()  # pyright: ignore[reportCallIssue]
