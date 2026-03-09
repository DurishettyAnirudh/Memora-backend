"""Notifications router — Telegram setup and VAPID-free notification scheduling."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class TelegramSetupRequest(BaseModel):
    telegram_chat_id: str


class TelegramSetupResponse(BaseModel):
    telegram_chat_id: str


@router.post("/telegram/setup", response_model=TelegramSetupResponse)
def setup_telegram(body: TelegramSetupRequest, db: Session = Depends(get_db)):
    """Save the user's Telegram chat ID for push notifications."""
    if not body.telegram_chat_id.strip():
        raise HTTPException(status_code=400, detail="chat_id cannot be empty")

    svc = SettingsService(db)
    user_settings = svc.get_settings()
    user_settings.telegram_chat_id = body.telegram_chat_id.strip()
    db.commit()
    return TelegramSetupResponse(telegram_chat_id=user_settings.telegram_chat_id)


@router.get("/telegram/setup")
def get_telegram_setup(db: Session = Depends(get_db)):
    """Return the saved Telegram chat ID (masked)."""
    svc = SettingsService(db)
    chat_id = svc.get_settings().telegram_chat_id
    return {"telegram_chat_id": chat_id, "configured": bool(chat_id)}
