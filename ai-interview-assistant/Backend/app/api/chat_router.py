from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api", tags=["openai"])

chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    reply = chat_service.chat(user_message=payload.message)
    return ChatResponse(reply=reply)
