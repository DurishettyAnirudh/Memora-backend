"""Search routes — FTS5 search across tasks."""

from fastapi import APIRouter, Query

from app.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, le=100),
):
    service = SearchService()
    return service.search_tasks(q, limit=limit)
