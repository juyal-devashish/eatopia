.PHONY: check backend-check web-check backend-dev web-dev

check: backend-check web-check

backend-check:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q

web-check:
	cd web && npm run check

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

web-dev:
	cd web && npm run dev
