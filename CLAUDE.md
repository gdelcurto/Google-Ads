# Google Ads Hotel Campaigns

Piattaforma interna Blastness/Mentefredda per la generazione automatica di campagne Google Ads nel settore hotel/turismo.

## Quick Start

```bash
# Setup completo (Docker)
make up
# Backend  -> http://localhost:8000
# API docs -> http://localhost:8000/api/docs
# Frontend -> http://localhost:80
# Login:     admin@blastness.com / admin123

# Dev locale (senza Docker)
make dev-backend    # uvicorn con reload su :8000
make dev-frontend   # Vite su :5173
make seed           # Crea DB + admin user

# Test
make test           # 53 test, pytest
cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -v --cov=app
```

## Architettura

```
Brief (JSON) -> Validators -> Generators -> Agents -> AccountPlan -> Export (CSV / Google Ads API)
```

Il **Brief** e' il source of truth: uno schema JSON immutabile che definisce brand, lingue, budget, obiettivi. Da un singolo brief il sistema genera l'intero account Google Ads (campagne, ad group, keyword, asset) per tutte le lingue configurate.

### Backend (Python FastAPI)

```
backend/app/
  main.py                  # Entry point + lifespan (migrations, seed admin)
  config.py                # Settings via env vars (pydantic-settings)
  auth.py                  # JWT (PyJWT + bcrypt)
  database.py              # SQLAlchemy 2.0 async (SQLite dev, PostgreSQL prod)
  skills.py                # Loader LRU-cached per skill markdown in docs/

  domain/
    models.py              # ORM: User, Project, CampaignRecord, AuditLog, ExportRecord, AutofillJob
    schemas/               # Pydantic v2: Brief, CampaignPlan, AccountPlan, etc.

  generators/              # Creano CampaignPlan da Brief
    orchestrator.py        # Esegue TUTTI i generator + agent validation in sequenza
    brand_search.py        # Search Brand (exact + phrase su brand terms)
    acquisition_search.py  # Search Acquisition (broad/modifier su category keywords)
    retargeting.py         # Display/Video/DemandGen su audience esistenti
    performance_max.py     # PMax con asset group + audience signals
    demand_gen.py          # Demand Gen creative-based

  agents/                  # Intelligence agents (classi Python, NON prompt .md)
    base.py                # CampaignAgent ABC + AgentLevel enum + ValidationIssue
    # L1 STRATEGIC (pre-generation: brief + strategy)
    account_architect.py
    budget_strategist.py
    bidding_strategist.py
    # L2 SPECIALIST (copy generation + per-campaign validation)
    brand.py
    acquisition.py
    retargeting.py
    performance_max.py
    demand_gen.py
    # TECH (cross-cutting)
    naming_enforcer.py
    negative_architect.py
    geo_specialist.py
    # L3 AUDITOR (post-generation cross-campaign)
    performance_auditor.py
    qa_gatekeeper.py

  connectors/
    claude_enricher.py     # Claude API: enrich brief, suggest copy/sitelinks/keywords
    ai_copy_generator.py   # AI headline/description enhancement
    ai_validator.py        # AI copy validation
    google_ads_api.py      # Google Ads API client (dry-run + live)
    csv_exporter.py        # Export per Google Ads Editor
    web_scraper.py         # Scraping sito hotel per autofill brief
    translation_provider.py # noop | google translate | deepl

  validators/
    brief_validator.py     # Schema + required fields
    strategy_validator.py  # Coerenza cross-campaign

  templates/
    presets.py             # Naming/UTM/label per preset (blastness, mentefredda)
    vertical_templates.py  # Keyword suggeriti per vertical (city_hotel, resort, boutique, etc.)

  routers/                 # API endpoints
    auth.py                # POST /api/auth/login, /logout
    projects.py            # CRUD /api/projects, PUT /api/projects/{id}/brief
    campaigns.py           # POST /api/projects/{id}/generate (dry_run param)
    export.py              # GET /api/projects/{id}/export/csv, POST .../publish
    autofill.py            # POST /api/projects/{id}/autofill-brief
    templates.py           # GET /api/templates/presets, /verticals
```

### Frontend (React 18 + TypeScript + Vite)

```
frontend/src/
  pages/
    LoginPage.tsx          # JWT login
    ProjectsPage.tsx       # Lista progetti + crea nuovo
    ProjectDetailPage.tsx  # Brief form, preview, plan, export/publish
  components/
    BriefForm.tsx          # Form multi-step (6 step)
    CampaignCard.tsx       # Preview campagna con budget/status/blockers
    ActionPlanTab.tsx      # Tree view campagne generate
    ApiLogTab.tsx          # Log richieste/risposte
    ScanLogTab.tsx         # Validation issues
  api/
    client.ts              # Axios + JWT auto-inject + 401 handling
    endpoints.ts           # Typed API functions
  contexts/                # React context providers
```

### Flusso di validazione dell'orchestrator

```
1. BriefValidator          schema + required fields
2. L1 Strategic agents     struttura brief + strategia (pre-generation)
3. Generators              creano CampaignPlan per ogni tipo x lingua
4. Idempotency diff        confronto con campagne esistenti
5. L2 Specialist agents    copy + per-campaign validation
6. StrategicValidator      coerenza cross-campaign
7. TECH agents             naming, negative keywords, geo targeting
8. L3 Audit agents         audit cross-campaign post-generation
```

## Modelli di dominio

| Model | Tabella | Ruolo |
|-------|---------|-------|
| User | users | Admin / Strategist / Operator (JWT auth) |
| Project | projects | Progetto cliente (draft -> validated -> preview -> published -> archived) |
| CampaignRecord | campaigns | Campagne generate, con external_key per idempotenza |
| ExportRecord | exports | CSV o API publish con metadata |
| AuditLog | audit_logs | Action log immutabile (user + timestamp) |
| AutofillJob | autofill_jobs | Job di scraping + AI enrichment (pending -> running -> completed/failed) |

Soft-delete su Project: `deleted_at` nullable. I record restano nel DB ma vengono filtrati.

## Tipi campagna

| Tipo | Generator | Agent L2 | Note |
|------|-----------|----------|------|
| search_brand | BrandSearchGenerator | BrandAgent | Exact + Phrase match su brand terms |
| search_acquisition | AcquisitionSearchGenerator | AcquisitionAgent | Broad/modifier su category keywords |
| retargeting | RetargetingGenerator | RetargetingAgent | Display/Video su audience remarketing |
| performance_max | PerformanceMaxGenerator | PMaxAgent | Asset group + audience signals |
| demand_gen | DemandGenGenerator | DemandGenAgent | Creative-based |

Ogni tipo x lingua = campagna separata. Brief con 5 tipi + 3 lingue = fino a 15 campagne.

## Skill files (docs/)

44 file markdown in `docs/` (01-44), caricati via `app.skills.load_skill()` con LRU cache.
Usati come system prompt per Claude API nelle chiamate di enrichment.

Skill principali usati dagli agent:
- `SEARCH_TERM_MINING` per keyword suggestions
- `AD_COPY_VARIANT_GENERATOR` per headline/description generation
- `BID_STRATEGY_RECOMMENDATIONS` per bid strategy
- `QUALITY_SCORE_BREAKDOWN` per QS audit
- `BUDGET_SCENARIO_PLANNER` per budget allocation
- `GOOGLE_ADS_AUDIT` per audit complessivo

## Database

- **Dev**: SQLite (`sqlite+aiosqlite:///./data/google_ads_campaigns.db`)
- **Prod**: PostgreSQL via Supabase (`postgresql+asyncpg://...`)
- **Migrations**: Alembic (auto-stamp da rev 002 se DB creato via create_all)
- Schema safety net in `main.py._ensure_missing_columns()` per colonne aggiunte post-create_all

## Naming conventions

Ogni preset (`blastness`, `mentefredda`) definisce:
- Pattern naming campagna: `{preset}_{brand_slug}_{type}_{lang}`
- UTM parameters e labels standard
- Vedi `backend/app/templates/presets.py`

## Env vars richieste

```bash
# Minime per dev locale (senza Google Ads API)
APP_ENV=development
DATABASE_URL=sqlite+aiosqlite:///./data/google_ads_campaigns.db
JWT_SECRET_KEY=<32+ chars>

# Per AI enrichment (autofill brief da sito hotel)
ANTHROPIC_API_KEY=sk-ant-...

# Per publish su Google Ads (opzionale, dry-run funziona senza)
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
```

## Test

```bash
make test
# oppure:
cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -v

# Con coverage:
cd backend && PYTHONPATH=. .venv/bin/pytest tests/ --cov=app --cov-report=term-missing
```

Fixtures in `backend/tests/conftest.py`:
- `sample_brief` - Brief completo da `examples/brief_complete.json`
- `minimal_brief` - Brief minimale per test veloci

## GAQL utili (debug Google Ads)

```sql
-- Campagne attive con budget
SELECT campaign.id, campaign.name, campaign.status,
       campaign_budget.amount_micros
FROM campaign
WHERE campaign.status = 'ENABLED'

-- Performance ultimi 30 giorni
SELECT campaign.name, metrics.impressions, metrics.clicks,
       metrics.cost_micros, metrics.conversions
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
ORDER BY metrics.cost_micros DESC

-- Keyword con QS basso
SELECT ad_group_criterion.keyword.text,
       ad_group_criterion.quality_info.quality_score
FROM keyword_view
WHERE ad_group_criterion.quality_info.quality_score < 5
  AND ad_group_criterion.status = 'ENABLED'

-- Search terms con conversioni
SELECT search_term_view.search_term, metrics.conversions,
       metrics.cost_micros, metrics.impressions
FROM search_term_view
WHERE metrics.conversions > 0
ORDER BY metrics.conversions DESC
```

## Deploy

- **Docker Compose**: `make up` (backend + frontend)
- **Railway**: configurato via `railway.toml`
- **FRONTEND_DIST_PATH**: env var per path esplicito del build frontend in Docker
