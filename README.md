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

## Deploy on Render

This repo now includes `Dockerfile` and `render.yaml` for Render deployment.

1. Push this repository to GitHub.
2. In Render, create a new Blueprint and connect this repo.
3. Render reads `render.yaml` and provisions the `memora-backend` web service.
4. Set secret values in Render dashboard for:
	- `OLLAMA_BASE_URL`
	- `OLLAMA_API_KEY`
	- `NOTIFICATION_SERVICE_URL`
	- `NOTIFICATION_API_KEY`
5. Deploy and verify health endpoint at `/health`.

Note: `DB_PATH` defaults to `/tmp/memora.db` in `render.yaml`, which is ephemeral and suitable for demos.
