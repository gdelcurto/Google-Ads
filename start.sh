#!/usr/bin/env bash
# ============================================================
#  Google Ads Hotel Campaigns — Quick Start (senza Docker)
#  Uso: ./start.sh
# ============================================================
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Prerequisiti ────────────────────────────────────────────
info "Controllo prerequisiti..."
command -v python3 >/dev/null 2>&1 || error "Python 3.11+ non trovato. Installa da https://python.org"
command -v node    >/dev/null 2>&1 || error "Node.js 18+ non trovato. Installa da https://nodejs.org"

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VERSION trovato"

# ── .env ────────────────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
    warning ".env non trovato — copio da .env.example"
    cp "$ROOT/.env.example" "$ROOT/.env"
    warning "Modifica $ROOT/.env con le tue credenziali Google Ads prima del deploy in produzione"
fi

# ── Backend setup ───────────────────────────────────────────
info "Setup backend..."
cd "$BACKEND"

if [ ! -d ".venv" ]; then
    info "Creazione virtual environment..."
    python3 -m venv .venv
fi

info "Installazione dipendenze Python..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

# Crea dir dati
mkdir -p "$ROOT/data/exports"

# Crea DB + seed admin
info "Inizializzazione database..."
PYTHONPATH="$BACKEND" .venv/bin/python -c "
import asyncio
from app.database import create_tables
asyncio.run(create_tables())
print('Database inizializzato')
"

# ── Frontend setup ───────────────────────────────────────────
info "Setup frontend..."
cd "$FRONTEND"

if [ ! -d "node_modules" ]; then
    info "Installazione dipendenze npm..."
    npm install --silent
fi

# ── Avvio servizi ───────────────────────────────────────────
info "Avvio backend (porta 8000)..."
cd "$BACKEND"
PYTHONPATH="$BACKEND" .venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info &
BACKEND_PID=$!

# Aspetta che il backend risponda
info "Attesa avvio backend..."
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
        info "Backend pronto"
        break
    fi
    sleep 1
done

info "Avvio frontend (porta 5173)..."
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

# ── Riepilogo ───────────────────────────────────────────────
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  App avviata con successo!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "  Backend API  →  http://localhost:8000"
echo -e "  Swagger docs →  http://localhost:8000/api/docs"
echo -e "  Frontend     →  http://localhost:5173"
echo ""
echo -e "  Login: ${YELLOW}admin@blastness.com${NC} / ${YELLOW}admin123${NC}"
echo ""
echo -e "  Premi ${RED}Ctrl+C${NC} per fermare tutti i servizi"
echo ""

# Aspetta e gestisci Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; info 'Servizi fermati'; exit 0" SIGINT SIGTERM
wait
