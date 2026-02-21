.PHONY: help up down build logs shell-backend test dev-backend dev-frontend seed

help:
	@echo ""
	@echo "Google Ads Hotel Campaigns — Comandi disponibili"
	@echo "=================================================="
	@echo ""
	@echo "  Docker (produzione locale)"
	@echo "  --------------------------"
	@echo "  make up            Avvia tutti i servizi (build + run)"
	@echo "  make down          Ferma e rimuove i container"
	@echo "  make build         Rebuilda le immagini Docker"
	@echo "  make logs          Segui i log di tutti i servizi"
	@echo "  make logs-backend  Segui i log del backend"
	@echo ""
	@echo "  Sviluppo (senza Docker)"
	@echo "  -----------------------"
	@echo "  make dev-backend   Avvia backend in modalità reload"
	@echo "  make dev-frontend  Avvia frontend Vite dev server"
	@echo "  make dev           Avvia backend + frontend (background)"
	@echo ""
	@echo "  Utility"
	@echo "  -------"
	@echo "  make test          Esegui test suite (53 test)"
	@echo "  make seed          Crea DB e admin user"
	@echo "  make shell-backend Shell nel container backend"
	@echo ""

# ── Docker ──────────────────────────────────────────────────────────────────

up:
	@[ -f .env ] || { echo "Copia .env.example in .env e configura le variabili"; cp .env.example .env; }
	@mkdir -p data/exports
	docker compose up --build -d
	@echo ""
	@echo "  Backend  → http://localhost:8000"
	@echo "  API docs → http://localhost:8000/api/docs"
	@echo "  Frontend → http://localhost:80"
	@echo ""
	@echo "  Login: admin@blastness.com / admin123"

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

shell-backend:
	docker compose exec backend bash

# ── Sviluppo locale ─────────────────────────────────────────────────────────

dev-backend:
	cd backend && \
	[ -d .venv ] || python3 -m venv .venv && \
	.venv/bin/pip install -q -r requirements.txt && \
	mkdir -p ../data/exports && \
	PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && \
	[ -d node_modules ] || npm install && \
	npm run dev

dev:
	@echo "Avvio backend (porta 8000) e frontend (porta 5173)..."
	@make dev-backend &
	@sleep 3 && make dev-frontend

# ── Utility ──────────────────────────────────────────────────────────────────

test:
	cd backend && \
	PYTHONPATH=. .venv/bin/pytest tests/ -v

seed:
	cd backend && \
	[ -d .venv ] || python3 -m venv .venv && \
	.venv/bin/pip install -q -r requirements.txt && \
	mkdir -p ../data/exports && \
	PYTHONPATH=. .venv/bin/python -c "\
import asyncio; \
from app.database import create_tables; \
asyncio.run(create_tables()); \
print('DB creato con successo')"
