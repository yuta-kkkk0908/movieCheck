.PHONY: help backend frontend up dev-a dev-b test test-backend test-frontend

help:
	@echo "Available commands:"
	@echo "  make backend        - Run backend only (FastAPI on :8001)"
	@echo "  make frontend       - Run frontend only (React on :3000)"
	@echo "  make up             - Run backend + frontend in one terminal"
	@echo "  make dev-a          - Alias for backend (for Terminal A)"
	@echo "  make dev-b          - Alias for frontend (for Terminal B)"
	@echo "  make test-backend   - Run backend tests (pytest)"
	@echo "  make test-frontend  - Run frontend tests (react-scripts test)"
	@echo "  make test           - Run backend + frontend tests"

backend:
	cd backend && python main.py

frontend:
	cd frontend && npm start

up:
	@set -e; \
	trap 'kill 0' INT TERM EXIT; \
	(cd backend && python main.py) & \
	(cd frontend && npm start) & \
	wait

dev-a: backend

dev-b: frontend

test-backend:
	@set -e; \
	cd backend; \
	python -m pytest -q

test-frontend:
	cd frontend && npm test -- --watchAll=false

test: test-backend test-frontend
