"""Chat routes — main chat endpoint and history."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConfirmRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Main chat endpoint. Processes user message through the NLU pipeline."""
    # Import here to avoid circular imports during startup
    from app.services.chat_service import ChatService

    service = ChatService(db)
    return await service.handle_message(
        request.message, request.session_id, request.history, request.utc_offset_minutes
    )


@router.get("/history")
def get_history(session_id: str | None = None, limit: int = 50):
    """Returns conversation history for a session."""
    # Will be populated once Memori integration is wired
    return {"session_id": session_id, "messages": [], "limit": limit}


@router.post("/confirm", response_model=ChatResponse)
async def confirm_action(
    request: ConfirmRequest,
    db: Session = Depends(get_db),
):
    """Handle user confirmation of a proposed action (e.g., conflict resolution)."""
    from app.services.chat_service import ChatService

    service = ChatService(db)
    return await service.handle_confirmation(request.session_id, request.option_id)
