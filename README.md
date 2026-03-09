# Memora Backend

AI-Powered Personal Life OS — Backend API service.

## Tech Stack

- **FastAPI** — API framework
- **SQLAlchemy** — ORM + SQLite
- **Alembic** — Database migrations
- **Memori BYODB** — Memory layer
- **APScheduler** — Background task scheduling
- **OpenAI client** — Ollama-compatible LLM calls

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
alembic upgrade head
python -m app.seed
```

## Development

```bash
make dev        # Start dev server
make test       # Run tests
make lint       # Run ruff + mypy
make migrate    # Run alembic migrations
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.
