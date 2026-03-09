"""Calendar routes — filtered event views, availability."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("")
def get_calendar_events(
    start: str = Query(..., description="Start date ISO format"),
    end: str = Query(..., description="End date ISO format"),
    domains: str | None = Query(None, description="Comma-separated domain IDs"),
    view: str = "week",
    db: Session = Depends(get_db),
):
    service = CalendarService(db)

    start_date = date.fromisoformat(start[:10])
    end_date = date.fromisoformat(end[:10])
    domain_ids = [int(d) for d in domains.split(",") if d.strip()] if domains else None

    return service.get_events(start_date, end_date, domain_ids, view)


@router.get("/availability")
def get_availability(
    target_date: str = Query(..., alias="date", description="Date ISO format"),
    duration_minutes: int = Query(60, description="Minimum slot duration"),
    db: Session = Depends(get_db),
):
    service = CalendarService(db)
    return service.get_availability(date.fromisoformat(target_date), duration_minutes)


@router.get("/week-load")
def get_week_load(
    week_start: str = Query(..., description="Monday date ISO format"),
    db: Session = Depends(get_db),
):
    service = CalendarService(db)
    return service.get_week_load(date.fromisoformat(week_start))
