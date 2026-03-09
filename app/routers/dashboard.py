"""Dashboard routes — today briefing and life metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db)):
    service = DashboardService(db)
    return service.get_today_briefing()


@router.get("/metrics")
def get_metrics(period: str = "week", db: Session = Depends(get_db)):
    service = DashboardService(db)
    return service.get_life_metrics(period=period)
