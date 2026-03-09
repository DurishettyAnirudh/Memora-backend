"""Memora Backend — FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.ai.client import init_ai
from app.services.domain_service import DomainService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB, AI, seed defaults."""
    # Initialize database tables
    init_db()

    # Initialize AI clients (Memori + Ollama)
    init_ai(settings.DB_PATH)

    # Seed default domains and settings
    db = SessionLocal()
    try:
        DomainService(db).seed_defaults()
        from app.services.settings_service import SettingsService
        SettingsService(db).get_settings()  # Creates defaults if missing
    finally:
        db.close()

    yield

    # Cleanup
    from app.services.notification_client import NotificationClient
    client = NotificationClient()
    await client.close()


app = FastAPI(
    title="Memora",
    description="AI-Powered Personal Life OS — Backend API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.routers import (  # noqa: E402
    chat,
    tasks,
    calendar,
    projects,
    domains,
    reminders,
    dashboard,
    memory,
    settings as settings_router,
    backup,
    search,
    notifications,
)

app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(calendar.router)
app.include_router(projects.router)
app.include_router(domains.router)
app.include_router(reminders.router)
app.include_router(dashboard.router)
app.include_router(memory.router)
app.include_router(settings_router.router)
app.include_router(backup.router)
app.include_router(search.router)
app.include_router(notifications.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}
