---
title: Core PPC Reasoning Framework
category: strategy
level: L1
agents: [AccountArchitect, BudgetStrategist, BiddingStrategist]
---

# Core PPC Reasoning Framework

Framework di ragionamento strategico trasversale per agenti L1.
Da usare quando si valutano decisioni su account structure, budget allocation e bidding strategy.

## 1. Alignment Chain

Ogni decisione tattica deve essere allineata a catena con l'obiettivo primario del brief:

```
Business Goal (brief.objectives.primary)
  -> KPI Target (brief.objectives.kpi)
    -> Campaign Type Selection
      -> Budget Allocation per Type
        -> Bid Strategy per Campaign
          -> Keyword / Audience Targeting
            -> Ad Copy & Landing Page
```

**Regola**: se un elemento della catena contraddice quello superiore, e' un errore di strategia.

Esempi:
- `primary: direct_bookings` + bid strategy Maximize Clicks = disallineamento (dovrebbe essere Target CPA o Target ROAS)
- `target_roas: 8.5` + budget 80% su retargeting con audience fredda = disallineamento
- `primary: brand_awareness` + budget 90% su Search Brand = inefficienza (dovrebbe investire su Display/PMax)

## 2. Profitability Hierarchy

Ordine di priorita' nell'allocazione budget per hotel con obiettivo conversioni:

```
1. Search Brand          (ROI piu' alto, difesa brand)
2. Search Acquisition    (intent alto, CPA prevedibile)
3. Performance Max       (automation Google, scala su audience)
4. Demand Gen            (awareness + consideration, CPA piu' alto)
5. Retargeting Display   (nurturing, volume limitato da audience size)
```

**Eccezioni documentate**:
- Hotel nuovo / brand sconosciuto: ridurre Search Brand, aumentare Acquisition + PMax
- Stagionalita': picchi di domanda giustificano shift temporaneo verso Acquisition
- Mercato saturo: retargeting piu' redditizio se CPC acquisition troppo alto

## 3. Budget Allocation Rules

### 3.1 Minimum viable budget per campaign type
| Tipo | Budget minimo mensile | Motivazione |
|------|----------------------|-------------|
| search_brand | EUR 200 | Serve copertura oraria completa su brand terms |
| search_acquisition | EUR 300 | Serve volume keyword sufficiente per ottimizzazione |
| retargeting | EUR 150 | Audience limited, sotto soglia non genera impression |
| performance_max | EUR 500 | Richiede learning period + asset rotation |
| demand_gen | EUR 400 | Richiede volume creative sufficiente |

### 3.2 Language split proporzionale
Budget per lingua deve rispettare il volume di ricerca stimato:
- Lingua primaria (paese hotel): 50-70% del budget tipo
- Lingue secondarie: proporzionale al traffico atteso

### 3.3 Red flags budget
- Budget totale < EUR 1500/mese con 4+ tipi campagna = troppo frammentato
- Singola campagna con < EUR 5/giorno = Google non riesce a ottimizzare
- Retargeting > 30% del budget totale = sproporzione (audience troppo piccola per assorbire)

## 4. Bidding Strategy Decision Tree

```
Obiettivo primario?
|
+-- direct_bookings
|   |-- Dati conversione disponibili (>30 conv/mese)?
|   |   +-- SI: Target ROAS (se target_roas definito) o Target CPA
|   |   +-- NO: Maximize Conversions (senza target, fase learning)
|   |
|   +-- Search Brand: Manual CPC o Target Impression Share (posizione 1)
|
+-- brand_awareness
|   +-- Search: Target Impression Share
|   +-- Display/PMax: Maximize Conversions (micro-conversioni: page view, scroll)
|
+-- phone_calls
|   +-- Target CPA (con conversion action = phone call)
|   +-- Search only: bid adjustment +20% mobile
```

## 5. Cross-Campaign Coherence Checks

Validazioni che gli agenti L1 devono eseguire sul brief completo:

### 5.1 Negative keyword isolation
- Brand terms del cliente DEVONO essere negative in Search Acquisition
- Category keywords generiche DEVONO essere negative in Search Brand
- Senza questa separazione: cannibalizzazione garantita

### 5.2 Landing page consistency
- Ogni campagna tipo x lingua deve avere una landing page
- La landing page deve essere nella lingua corretta
- PMax e Demand Gen possono usare pagine diverse (asset-specific)

### 5.3 Conversion tracking alignment
- Tutte le campagne devono puntare alla stessa `primary_conversion_action`
- Se ci sono secondary conversions, non devono essere impostate come primary in nessuna campagna
- PMax: conversion value deve essere configurato (obbligatorio per ROAS bidding)

### 5.4 Geographic coherence
- Target countries nel brief devono matchare le lingue configurate
- Se target_countries include "DE" ma nessuna lingua DE configurata: warning
- Hotel in IT con target solo "US": probabile errore (aggiungere IT)

## 6. Copy Quality Gates

Regole trasversali per tutte le campagne (Google Ads policy + best practice):

### 6.1 Limiti caratteri Google Ads
| Asset | Max chars | Note |
|-------|-----------|------|
| Headline | 30 | 15 obbligatori per RSA |
| Description | 90 | 4 obbligatori per RSA |
| Sitelink text | 25 | |
| Sitelink description | 35 | 2 righe |
| Callout | 25 | |
| Long headline (PMax) | 90 | |
| Business name | 25 | |

### 6.2 Diversita' copy
- RSA: almeno 3 headline uniche (non varianti minime)
- Almeno 1 headline con brand name
- Almeno 1 headline con CTA (Prenota, Scopri, Chiama)
- Almeno 1 description con USP unico

### 6.3 Policy compliance
- No superlativo assoluto senza prova ("il migliore hotel" -> warning)
- No prezzo specifico in headline (cambia, landing page e' source of truth)
- No ALL CAPS (tranne acronimi: "SPA", "B&B", "Wi-Fi")
- No simboli ripetuti ("!!!", "***", ">>>")
- No claim medici/sanitari senza certificazione

## 7. Seasonal Adjustment Framework

Per hotel, la stagionalita' impatta direttamente budget e strategia:

| Periodo | Azione budget | Azione bidding |
|---------|---------------|----------------|
| Alta stagione (booking window) | +30-50% Acquisition + PMax | Aumentare target CPA/ROAS |
| Bassa stagione | Ridurre Acquisition, mantenere Brand | Ridurre target, focus profittabilita' |
| Last minute (< 7gg) | Shift verso Brand + Retargeting | Aggressive su audience calda |
| Early booking (> 90gg) | Aumentare PMax + DemandGen | Focus awareness, CPA piu' alto accettabile |

## Uso nel sistema

Questo framework e' caricato via `app.skills.load_skill()` e usato come context per gli agenti L1
(AccountArchitect, BudgetStrategist, BiddingStrategist) durante la fase di validazione pre-generation.

```python
from app.skills import load_skill
CORE_PPC_FRAMEWORK = "45-core-ppc-reasoning-framework.md"
system_prompt = load_skill(CORE_PPC_FRAMEWORK)
```
