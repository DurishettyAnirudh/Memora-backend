.PHONY: dev test lint migrate shell

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/
	mypy app/

migrate:
	alembic upgrade head

shell:
	python -i -c "from app.database import *; from app.models import *"
