"""Reminder routes — CRUD, snooze, dismiss."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.reminder import ReminderCreate, ReminderResponse, SnoozeRequest
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderResponse])
def list_reminders(
    task_id: int | None = None,
    is_fired: bool | None = None,
    db: Session = Depends(get_db),
):
    service = ReminderService(db)
    return service.list_reminders(task_id=task_id, is_fired=is_fired)


@router.post("", response_model=ReminderResponse, status_code=201)
def create_reminder(data: ReminderCreate, db: Session = Depends(get_db)):
    service = ReminderService(db)
    return service.create_reminder(data)


@router.post("/{reminder_id}/snooze", response_model=ReminderResponse)
def snooze_reminder(
    reminder_id: int, data: SnoozeRequest, db: Session = Depends(get_db)
):
    service = ReminderService(db)
    reminder = service.snooze_reminder(reminder_id, data.duration)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.post("/{reminder_id}/dismiss", status_code=204)
def dismiss_reminder(reminder_id: int, db: Session = Depends(get_db)):
    service = ReminderService(db)
    if not service.dismiss_reminder(reminder_id):
        raise HTTPException(status_code=404, detail="Reminder not found")
