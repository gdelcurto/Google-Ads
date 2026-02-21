# ── Stage 1: Build React frontend ─────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --prefer-offline
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python backend + embedded frontend ────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ .

# Embed the built React app so FastAPI can serve it
COPY --from=frontend-builder /build/dist ./frontend/dist

# Tell main.py where the frontend dist is
ENV FRONTEND_DIST_PATH=/app/frontend/dist

RUN mkdir -p /app/data/exports

EXPOSE 8000

# Railway injects $PORT; fall back to 8000 for local docker run
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
