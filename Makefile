.PHONY: check backend-check web-check infra-check backend-dev web-dev migrate e2e

check: backend-check web-check infra-check

backend-check:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q

web-check:
	cd web && npm run check

infra-check:
	cd .railway && npm ci --silent && ../web/node_modules/.bin/tsc -p .

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

migrate:
	cd backend && uv run alembic upgrade head

e2e:
	cd web && npx playwright test

web-dev:
	cd web && npm run dev
