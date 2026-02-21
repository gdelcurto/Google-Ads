# Google Ads Hotel Campaigns

Piattaforma interna per la generazione automatizzata di campagne Google Ads nel settore hotel/turismo.
Sviluppata per **Blastness / Mentefredda**.

---

## Funzionalità

- **5 tipologie di campagna**: Search Brand, Search Acquisition, Retargeting, Performance Max, Demand Gen
- **Multi-lingua**: IT, EN, DE, FR, ES (e qualsiasi altra lingua configurata nel brief)
- **Validazione brief** con checklist, errori e warning strutturati
- **Preview struttura** ad albero (campagne → ad group → keyword → asset)
- **Export CSV** compatibile con Google Ads Editor (import diretto)
- **Publish API** via Google Ads API (dry run + live)
- **Template verticali**: city_hotel, resort, boutique, business, agriturismo
- **Preset agenzia**: Blastness, Mentefredda (naming, UTM, label standardizzati)
- **Idempotenza**: rilancio sicuro senza duplicati (basato su external_key)
- **Audit log**: ogni azione tracciata con utente e timestamp
- **Auth**: JWT con ruoli Admin / Strategist / Operator

---

## Stack

| Layer | Tech |
|-------|------|
| API Backend | Python 3.11+ · FastAPI · Pydantic v2 |
| ORM + Migrations | SQLAlchemy 2.0 · Alembic |
| Database | SQLite (dev) — PostgreSQL-ready |
| Auth | JWT (PyJWT) · bcrypt |
| Google Ads | google-ads Python SDK v24 |
| Testing | pytest · pytest-asyncio |
| Frontend | React 18 · TypeScript · Vite |
| HTTP Client | axios · @tanstack/react-query |

---

## Installazione rapida

### Prerequisiti

- Python 3.11+
- Node.js 18+
- (Opzionale) Google Ads API credentials

### 1. Clone e setup

```bash
git clone <repo>
cd Google-Ads
```

### 2. Backend

```bash
cd backend

# Ambiente virtuale
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Dipendenze
pip install -r requirements.txt

# Configurazione
cp ../.env.example .env
# Modifica .env con i tuoi valori

# Crea il database
mkdir -p data
python -c "import asyncio; from app.database import create_tables; asyncio.run(create_tables())"

# (Alternativa con Alembic)
alembic upgrade head

# Avvia il server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API disponibile su: http://localhost:8000
Docs Swagger: http://localhost:8000/api/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend su: http://localhost:5173

### 4. Login default

```
Email:    admin@blastness.com
Password: admin123   (cambia in .env prima del deploy)
```

---

## Struttura progetto

```
Google-Ads/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Settings da env vars
│   │   ├── auth.py                    # JWT auth utilities
│   │   ├── database.py                # SQLAlchemy async engine
│   │   ├── domain/
│   │   │   ├── models.py              # SQLAlchemy ORM models
│   │   │   └── schemas/
│   │   │       ├── brief.py           # Pydantic: Brief (source of truth)
│   │   │       └── campaign_plan.py   # Pydantic: AccountPlan, CampaignPlan
│   │   ├── generators/
│   │   │   ├── base.py                # Utility base class
│   │   │   ├── brand_search.py        # Search Brand generator
│   │   │   ├── acquisition_search.py  # Search Acquisition generator
│   │   │   ├── retargeting.py         # Retargeting Display generator
│   │   │   ├── performance_max.py     # PMax generator
│   │   │   ├── demand_gen.py          # Demand Gen generator
│   │   │   └── orchestrator.py        # Coordina tutti i generator
│   │   ├── connectors/
│   │   │   ├── csv_exporter.py        # Google Ads Editor CSV export
│   │   │   ├── google_ads_api.py      # Google Ads API connector
│   │   │   └── translation_provider.py# NoOp / Google / DeepL
│   │   ├── validators/
│   │   │   └── brief_validator.py     # Validazione brief (schema + business rules)
│   │   ├── templates/
│   │   │   ├── presets.py             # Blastness / Mentefredda presets
│   │   │   └── vertical_templates.py  # Keyword templates per verticale
│   │   └── routers/
│   │       ├── auth.py                # /api/auth/*
│   │       ├── projects.py            # /api/projects/*
│   │       ├── campaigns.py           # /api/projects/{id}/generate
│   │       ├── export.py              # /api/projects/{id}/export/csv + publish
│   │       └── templates.py           # /api/templates/*
│   ├── migrations/                    # Alembic migrations
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_validators.py
│   │   └── test_generators.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/                     # Login, Projects, ProjectDetail
│       ├── components/                # Layout
│       └── api/                       # axios client + typed endpoints
├── examples/
│   └── brief_complete.json            # Esempio brief completo (Grand Hotel Roma)
├── docs/
│   └── design.md                      # Documento di design
└── .env.example
```

---

## Configurazione Google Ads API

### 1. Developer Token

1. Accedi a [Google Ads](https://ads.google.com)
2. Vai su **Strumenti → Centro API**
3. Richiedi un Developer Token (Basic access per test)

### 2. OAuth2 Credentials

1. Vai su [Google Cloud Console](https://console.cloud.google.com)
2. Crea un progetto e abilita **Google Ads API**
3. Crea credenziali OAuth2 (Desktop application)
4. Scarica il `client_secret.json`

### 3. Refresh Token

```bash
pip install google-auth-oauthlib
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    scopes=['https://www.googleapis.com/auth/adwords']
)
creds = flow.run_local_server(port=0)
print('REFRESH TOKEN:', creds.refresh_token)
"
```

### 4. Configura .env

```bash
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token
GOOGLE_ADS_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your-client-secret
GOOGLE_ADS_REFRESH_TOKEN=your-refresh-token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=000-000-0001  # MCC ID
```

---

## Utilizzo API

### Flusso completo

```bash
BASE=http://localhost:8000/api

# 1. Login
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -d "username=admin@blastness.com&password=admin123" \
  | jq -r .access_token)

# 2. Crea progetto
PROJECT=$(curl -s -X POST "$BASE/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Grand Hotel Roma Q2","client_slug":"grand-hotel-roma","preset":"blastness","vertical":"city_hotel"}' \
  | jq -r .id)

# 3. Carica brief
curl -X PUT "$BASE/projects/$PROJECT/brief" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @examples/brief_complete.json

# 4. Genera piano (dry run)
curl -X POST "$BASE/projects/$PROJECT/generate?dry_run=true" \
  -H "Authorization: Bearer $TOKEN"

# 5. Esporta CSV
curl -o export.csv "$BASE/projects/$PROJECT/export/csv" \
  -H "Authorization: Bearer $TOKEN"

# 6. Publish (dry run — simula senza chiamare Google)
curl -X POST "$BASE/projects/$PROJECT/publish?dry_run=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Test

```bash
cd backend
source .venv/bin/activate

# Tutti i test
pytest tests/ -v

# Solo validator
pytest tests/test_validators.py -v

# Con coverage
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Naming Convention

```
{LANG} | {TYPE} | {SUBTYPE} | {MATCH_TYPE}

Esempi:
  IT | Search | Brand | Exact
  EN | Search | Acquisition | Broad
  FR | PMax | Hotel | –
  DE | Retargeting | Display | –
  IT | DemandGen | Remarketing | –
```

## UTM Template (Blastness)

```
{lpurl}?utm_source=google
       &utm_medium={network}
       &utm_campaign={campaignid}
       &utm_content={adgroupid}
       &utm_term={keyword}
       &device={device}
       &matchtype={matchtype}
       &utm_preset=blastness
```

---

## Flusso Demand Gen / Display (assets mancanti)

Se le creatività non sono fornite nel brief:
1. Il generator crea placeholder `TODO: ...`
2. Il campo `can_publish: false` blocca la pubblicazione API
3. Il CSV viene esportato comunque con le note TODO
4. L'operatore carica i file e ri-lancia il publish

---

## Multi-lingua

Ogni campagna viene generata per ogni lingua configurata nel brief, con:
- Budget specifico per lingua (da `budgets.by_campaign_type.{type}.by_language`)
- Landing page specifica per lingua
- Asset (headline, description, sitelink) specifici per lingua
- Language targeting ID Google corretto

---

## Sicurezza

- Credenziali mai hardcoded — solo `.env` (non committato)
- JWT token con scadenza configurabile
- Ruoli: `admin` > `strategist` > `operator`
- Audit log immutabile per ogni azione

---

## Feedback e Issues

Segnala problemi su: https://github.com/your-org/google-ads-hotel-campaigns/issues
