// ── Shared constants for project detail components ────────────────────────────

export const TYPE_COLOR: Record<string, string> = {
  search_brand:       '#1a73e8',
  search_acquisition: '#ea8600',
  retargeting:        '#7c3aed',
  performance_max:    '#059669',
  demand_gen:         '#e10098',
}

export const TYPE_LABEL: Record<string, string> = {
  search_brand:       'Brand',
  search_acquisition: 'Acquisition',
  retargeting:        'Retargeting',
  performance_max:    'Performance Max',
  demand_gen:         'Demand Gen',
}

export const CAMPAIGN_STRATEGY: Record<string, {
  label: string; funnel: string; funnelColor: string; priority: number
  description: string; audience: string; kpi: string; formats: string
}> = {
  search_brand: {
    label: 'Brand Search', funnel: 'Bottom', funnelColor: '#dc2626', priority: 1,
    description:
      'Protegge il traffico di brand dalle OTA (Booking.com, Expedia) che fanno bidding sul nome dell\'hotel. ' +
      'Intercetta utenti con la più alta intenzione d\'acquisto al CPC più contenuto. ' +
      'Fondamentale per garantire il flusso di prenotazioni dirette e massimizzare il ROAS complessivo dell\'account.',
    audience: 'Utenti che cercano direttamente il nome dell\'hotel o varianti brand',
    kpi: 'ROAS atteso 5:1–10:1 · CPC basso · CTR alto · Priorità massima',
    formats: 'RSA (Responsive Search Ads) con brand name in posizione 1',
  },
  search_acquisition: {
    label: 'Acquisition Search', funnel: 'Mid → Bottom', funnelColor: '#d97706', priority: 2,
    description:
      'Intercetta viaggiatori in fase di ricerca attiva su keyword di destinazione, categoria e servizi ' +
      '(es. "hotel 4 stelle Roma centro", "hotel con spa lago di Garda"). ' +
      'È il principale motore di acquisizione di nuovi clienti diretti, indirizzando il traffico verso il sito ufficiale invece che verso le OTA.',
    audience: 'Viaggiatori in fase di ricerca attiva che non conoscono ancora il brand',
    kpi: 'ROAS atteso 3:1–5:1 · Volume elevato · CPA target per conversione diretta',
    formats: 'RSA con copy differenziato per tema (location, servizi, categoria, occasione)',
  },
  performance_max: {
    label: 'Performance Max', funnel: 'Full-Funnel', funnelColor: '#059669', priority: 3,
    description:
      'Campagna automatizzata di Google che scala su tutti i touchpoint: Search, Display, YouTube, Maps, Gmail e Discover. ' +
      'Ottimizza autonomamente la distribuzione del budget verso le conversioni più probabili, ' +
      'amplificando i risultati delle campagne brand e acquisition con reach incrementale su tutti i canali.',
    audience: 'Audience automatica basata su segnali di remarketing, liste in-market e customer match',
    kpi: 'ROAS target configurabile · Apprendimento: 4–6 settimane · Richiede asset visivi',
    formats: 'Asset group con headline, descrizioni lunghe, immagini landscape/square e video YouTube',
  },
  retargeting: {
    label: 'Retargeting Display', funnel: 'Mid → Bottom', funnelColor: '#7c3aed', priority: 4,
    description:
      'Re-intercetta i visitatori del sito che hanno esplorato le camere o il motore di prenotazione senza completare la prenotazione. ' +
      'Utilizza messaggi di urgency e rassicurazione per spingere alla conversione diretta, ' +
      'con costi di acquisizione inferiori rispetto alle campagne di prospecting.',
    audience: 'Visitatori del sito negli ultimi 14–30 giorni, esclusi i clienti già prenotati',
    kpi: 'CPA inferiore all\'acquisition · Alta probabilità di conversione · Reach limitato ma qualificato',
    formats: 'Display ads adattivi con immagini hotel (300×250, 728×90, 160×600)',
  },
  demand_gen: {
    label: 'Demand Gen', funnel: 'Top', funnelColor: '#e10098', priority: 5,
    description:
      'Campagna di ispirazione su YouTube, Google Discover e Gmail che raggiunge i viaggiatori nella fase pre-ricerca, ' +
      'quando ancora stanno pianificando la prossima vacanza. ' +
      'Genera notorietà del brand, alimenta le audience di remarketing e prepara il terreno per le campagne di performance.',
    audience: 'Audience in-market per hotel e viaggi, similar audiences e prospecting su YouTube',
    kpi: 'Focus su reach e consideration · Risultati a 4–8 settimane · Richiede video e creatività visive',
    formats: 'Video 16:9 su YouTube, immagini landscape e square su Discover e Gmail',
  },
}
