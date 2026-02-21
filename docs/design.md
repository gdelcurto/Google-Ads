# Google Ads Hotel Campaigns — Design Document

## 1. Scelte Architetturali

### Linguaggio: Python + FastAPI

**Motivazione:**
- `google-ads` Python client library è la più matura e completa (v26+)
- FastAPI + Pydantic = validazione automatica + OpenAPI docs senza boilerplate
- SQLAlchemy + Alembic per ORM + migrazioni reproducibili
- Ecosistema ideale per data manipulation (campagne = dati strutturati)
- Testing con pytest è più rapido da scaffoldare rispetto a Jest/Vitest

**Alternativa scartata (TypeScript/Node):**
- `google-ads-api` Node library meno documentata e con breaking changes più frequenti
- Overhead di setup (ts-node, ESM, ecc.) senza vantaggi tangibili per questo dominio

### Frontend: React + TypeScript (minimale)

- SPA leggera su Vite + React
- Comunica via REST con il backend
- Nessun SSR: i dati sono sensibili, si caricano on-demand, non serve SEO

---

## 2. Source of Truth vs Dati Derivati

| Dato | Natura | Note |
|------|--------|-------|
| Brief JSON | **Source of Truth** | Immutabile dopo approvazione strategist |
| Naming campagne | Derivato | Calcolato da brief + naming convention |
| Keywords (brand) | SoT (nel brief) | Forniti dallo strategist |
| Keywords (acquisition) | Derivato + SoT | Template verticale + review strategist |
| Traduzioni USP/asset | Derivato | Dal brief (lingue) o provider esterno |
| UTM template | Derivato | Centralizzato, configurabile per preset |
| Audience signals PMax | Derivato | Da remarketing + in-market del brief |
| Budget | SoT | Dal brief, per tipo campagna + lingua |

---

## 3. Flusso Applicativo

```
Strategist → Compila Brief → Validazione → Preview struttura
                                               ↓
                                     Dry Run (diff)
                                               ↓
                          ┌──────────────────────────────────┐
                          │  Export CSV (Google Ads Editor)  │
                          │  Publish API (toggle)            │
                          └──────────────────────────────────┘
                                               ↓
                                          Audit Log
```

---

## 4. Naming Convention

```
{LANG} | {TYPE} | {SUBTYPE} | {MATCH_TYPE}

Esempi:
  IT | Search | Brand | Exact
  EN | Search | Acquisition | Broad
  FR | PMax | Hotel | –
  DE | Retargeting | Display | –
  IT | DemandGen | Remarketing | –
```

**Label standard Blastness/Mentefredda:**
```
blastness_setup, blastness_{client_slug}, blastness_{quarter}
```

---

## 5. UTM Template Centralizzato

```
{lpurl}?utm_source=google
       &utm_medium={network}
       &utm_campaign={campaignid}
       &utm_content={adgroupid}
       &utm_term={keyword}
       &utm_device={device}
       &utm_matchtype={matchtype}
       &utm_preset=blastness
```

---

## 6. Idempotenza

Ogni campagna generata è identificata univocamente da:
```
{preset}_{client_slug}_{lang}_{campaign_type}_{subtype}_{version}
```

Al rilanciamento: se esiste già una campagna con lo stesso `external_key`, aggiorna invece di creare.

---

## 7. Moduli Principali

### generators/
- `BrandSearchGenerator` — Exact + Phrase, negative non-brand, RSA brand-tone
- `AcquisitionSearchGenerator` — Keyword list tematica, RSA USP, negative brand
- `RetargetingGenerator` — Display/Video/DemandGen su audience esistenti
- `PerformanceMaxGenerator` — Asset group per lingua, audience signals, final URL expansion
- `DemandGenGenerator` — Asset placeholder con blocco publish se mancanti

### connectors/
- `GoogleAdsApiConnector` — Stub completo + guida credenziali reali
- `AdsEditorCsvExporter` — CSV Google Ads Editor (multi-sheet simulato)
- `TranslationProvider` — Abstract + implementazioni: NoOp, Google Translate, DeepL

### validators/
- Schema validation (Pydantic, automatica)
- Business rules: budget min, keyword count, RSA headline/description limits, policy constraints

---

## 8. Tradeoff e Limitazioni

| Problema | Decisione |
|----------|-----------|
| Google Ads API richiede credenziali OAuth2 | Stub con dry-run; guida setup in README |
| DemandGen: creatività non sempre presenti | Blocca publish, genera TODO list nell'export |
| Traduzioni automatiche: qualità variabile | Provider NoOp (pass-through) di default; Google Translate/DeepL opzionali |
| PMax: final URL expansion management | Configurabile nel brief; default OFF per hotel (controllo landing) |
| Keyword expansion automatica | Template verticale come suggerimento; approvazione strategist obbligatoria |

---

## 9. Template Verticali

| Verticale | Caratteristiche |
|-----------|-----------------|
| `city_hotel` | Keywords business/location, USP: posizione centrale, servizi business |
| `resort` | Keywords leisure/famiglia/relax, USP: piscina, spiaggia, all-inclusive |
| `boutique` | Keywords lusso/esperienza/charme, USP: unicità, personalization |

---

## 10. Stack Tecnologico

| Layer | Tech |
|-------|------|
| API | FastAPI 0.110+ |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (PyJWT) + bcrypt |
| DB | SQLite (dev) / PostgreSQL-ready |
| Testing | pytest + httpx |
| Frontend | React 18 + TypeScript + Vite |
| Google Ads | google-ads-google (v26+) |
| CSV | csv stdlib + pandas |
