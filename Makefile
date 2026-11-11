.PHONY: up down test lint eval clean backend frontend

up:
	docker compose up -d

down:
	docker compose down

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest backend/tests -v

lint:
	ruff check backend
	mypy backend/app/domain backend/app/application

eval:
	python -m backend.app.application.use_cases.run_evaluation

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
