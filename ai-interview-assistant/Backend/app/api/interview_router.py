from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.interview import Message, MessageRole
from app.models.schemas import (
    AnswerRequest,
    ArchiveInterviewRequest,
    ArchiveInterviewResponse,
    InterviewConfigRequest,
    InterviewModeRequest,
    InterviewListResponse,
    InterviewResponse,
    SummaryView,
)
from app.services import tts_service
from app.services.interview_ai_service import InterviewAIService, get_interview_ai_service
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def get_interview_service(
    db: Session = Depends(get_db),
    ai: InterviewAIService = Depends(get_interview_ai_service),
) -> InterviewService:
    return InterviewService(db=db, ai=ai)


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: InterviewConfigRequest,
    background_tasks: BackgroundTasks,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    return service.create(payload, background_tasks=background_tasks)


@router.get("", response_model=InterviewListResponse)
def list_interviews(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    archived: bool = Query(default=False),
    service: InterviewService = Depends(get_interview_service),
) -> InterviewListResponse:
    return service.list_sessions(limit=limit, offset=offset, archived=archived)

@router.patch("/{session_id}/archive", response_model=ArchiveInterviewResponse)
def archive_interview(
    session_id: UUID,
    payload: ArchiveInterviewRequest,
    service: InterviewService = Depends(get_interview_service),
) -> ArchiveInterviewResponse:
    return service.archive(session_id=session_id, archived=payload.archived)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(
    session_id: UUID,
    service: InterviewService = Depends(get_interview_service),
) -> Response:
    service.delete(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}", response_model=InterviewResponse)
def get_interview(
    session_id: UUID,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    return service.get(session_id)


@router.patch("/{session_id}/mode", response_model=InterviewResponse)
def set_interview_mode(
    session_id: UUID,
    payload: InterviewModeRequest,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    return service.set_mode(session_id, payload)


@router.post("/{session_id}/answer", response_model=InterviewResponse)
def answer_interview(
    session_id: UUID,
    payload: AnswerRequest,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    return service.answer(session_id, payload)


@router.post("/{session_id}/skip", response_model=InterviewResponse)
def skip_question(
    session_id: UUID,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    return service.skip(session_id)


@router.post("/{session_id}/end", response_model=InterviewResponse)
def end_interview(
    session_id: UUID,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    return service.end(session_id)


@router.get("/{session_id}/summary", response_model=SummaryView)
def get_summary(
    session_id: UUID,
    service: InterviewService = Depends(get_interview_service),
) -> SummaryView:
    return service.summary(session_id)


@router.get("/{session_id}/messages/{message_id}/audio")
def message_audio(
    session_id: UUID,
    message_id: UUID,
    voice: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    """Text-to-speech for a single interviewer message (Workshop 3)."""
    message = db.execute(
        select(Message).where(Message.id == message_id, Message.session_id == session_id)
    ).scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if message.role != MessageRole.ASSISTANT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio is only available for interviewer questions.",
        )

    config = message.session.config or {}
    language = config.get("language", "en")
    try:
        audio = tts_service.get_or_create_audio(message.content, language=language, speaker=voice)
    except tts_service.TtsUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Text-to-speech failed."
        ) from exc

    etag = f'"{tts_service.cache_key(message.content, language, voice)}"'
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "public, max-age=31536000, immutable", "ETag": etag},
    )
