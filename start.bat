@echo off
REM ============================================================
REM  Google Ads Hotel Campaigns — Quick Start (Windows)
REM  Uso: doppio click su start.bat oppure dal terminale
REM ============================================================
setlocal EnableDelayedExpansion

set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%frontend

echo.
echo  Google Ads Hotel Campaigns — Avvio...
echo  ======================================
echo.

REM ── Prerequisiti ────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato. Installa da https://python.org ^(versione 3.11+^)
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Node.js non trovato. Installa da https://nodejs.org ^(versione 18+^)
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] %PYVER% trovato

REM ── .env ────────────────────────────────────────────────────
if not exist "%ROOT%.env" (
    echo [AVVISO] .env non trovato — copio da .env.example
    copy "%ROOT%.env.example" "%ROOT%.env" >nul
)

REM ── Backend setup ───────────────────────────────────────────
echo [INFO] Setup backend...
cd /d "%BACKEND%"

if not exist ".venv" (
    echo [INFO] Creazione virtual environment...
    python -m venv .venv
)

echo [INFO] Installazione dipendenze Python...
call .venv\Scripts\pip install --quiet --upgrade pip
call .venv\Scripts\pip install --quiet -r requirements.txt

REM Crea cartella dati
if not exist "%ROOT%data\exports" mkdir "%ROOT%data\exports"

REM Inizializza DB
echo [INFO] Inizializzazione database...
set PYTHONPATH=%BACKEND%
call .venv\Scripts\python -c "import asyncio; from app.database import create_tables; asyncio.run(create_tables()); print('[OK] Database inizializzato')"

REM ── Frontend setup ───────────────────────────────────────────
echo [INFO] Setup frontend...
cd /d "%FRONTEND%"

if not exist "node_modules" (
    echo [INFO] Installazione dipendenze npm...
    call npm install --silent
)

echo [INFO] Build frontend...
call npm run build
if errorlevel 1 (
    echo [ERRORE] Build frontend fallita
    pause
    exit /b 1
)

REM ── Avvio servizi ───────────────────────────────────────────
echo.
echo [INFO] Avvio backend su http://localhost:8000 ...
cd /d "%BACKEND%"
set PYTHONPATH=%BACKEND%
start "Backend - Google Ads" cmd /k ".venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [INFO] Attesa avvio backend...
timeout /t 4 /nobreak >nul

REM ── Riepilogo ───────────────────────────────────────────────
echo.
echo  ================================================
echo   App avviata con successo!
echo  ================================================
echo.
echo   Apri il browser su:
echo.
echo   http://localhost:8000
echo.
echo   Swagger docs -^>  http://localhost:8000/api/docs
echo   Login: admin@blastness.com / admin123
echo.
echo   Chiudi la finestra "Backend" per fermare.
echo.
pause
