import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat_router import router as chat_router
from app.api.health_router import router as health_router
from app.api.interview_router import router as interview_router
from app.api.project_router import router as project_router
from app.config.settings import get_settings

settings = get_settings()
app = FastAPI(title="AI Interview Assistant", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(interview_router)
app.include_router(project_router)


@app.on_event("startup")
def _warm_up_tts() -> None:
    # Optionally pre-load the TTS model so the first speak request isn't a cold start.
    if not settings.tts_warm_up_on_start:
        return

    def _run() -> None:
        try:
            from app.services import tts_service

            tts_service.warm_up()
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).warning("TTS warm-up failed", exc_info=True)

    threading.Thread(target=_run, daemon=True).start()
