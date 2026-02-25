import React, { useState } from 'react'
import { FormState } from '../types'
import { css, langPillStyle } from '../styles'
import { T } from '../../../styles/theme'

interface Props {
  form: FormState
  setField: (key: keyof FormState, val: string) => void
  autofillUrl: string
  setAutofillUrl: (url: string) => void
  autofillLangs: string[]
  toggleAutofillLang: (code: string) => void
  autofillManual: boolean
  setAutofillManual: React.Dispatch<React.SetStateAction<boolean>>
  autofillContent: string
  setAutofillContent: (v: string) => void
  autofillSuccess: boolean
  startJobMutation: { mutate: () => void; isPending: boolean; isSuccess: boolean }
  setErrors: (errs: string[]) => void
  hasExistingBrief?: boolean
}

/* ── colour palette derived from T.blue (#576a8f) ─────────────────────── */
const BLUE = T.blue           // #576a8f
const BLUE_DARK = '#3e4f6e'   // darker shade for text on light bg
const BLUE_LIGHT = '#e9edf4'  // very light bg tint
const BLUE_MID = '#c5cedf'    // border / inactive pills

export function Step0InfoBase({
  form, setField,
  autofillUrl, setAutofillUrl, autofillLangs, toggleAutofillLang,
  autofillManual, setAutofillManual, autofillContent, setAutofillContent,
  autofillSuccess, startJobMutation, setErrors,
  hasExistingBrief,
}: Props) {
  const [showNewScan, setShowNewScan] = useState(false)

  /* ── Scan panel (full form) ───────────────────────────────────────── */
  const scanPanel = (
    <div style={css.autofillPanel}>
      <div style={css.autofillTitle}>
        <i className="fa-solid fa-wand-magic-sparkles"></i> Auto-compila dal sito dell'hotel
      </div>
      <div style={css.autofillSubtitle}>
        Inserisci l'URL del sito dell'hotel: l'AI analizzerà il sito e compilerà automaticamente
        tutti i campi del brief. L'elaborazione avviene in background — puoi cambiare scheda
        e tornerai notificato quando è pronta.
      </div>
      <div style={css.autofillRow}>
        <input
          style={css.autofillUrlInput}
          type="url"
          value={autofillUrl}
          onChange={e => { setAutofillUrl(e.target.value); }}
          placeholder="https://www.nomedelhotel.it"
          disabled={startJobMutation.isPending || startJobMutation.isSuccess}
        />
        <button
          style={{ ...css.btnAutofill, opacity: startJobMutation.isPending || startJobMutation.isSuccess || !autofillUrl.trim() ? 0.6 : 1 }}
          onClick={() => { setErrors([]); startJobMutation.mutate() }}
          disabled={startJobMutation.isPending || startJobMutation.isSuccess || !autofillUrl.trim()}
        >
          {startJobMutation.isPending
            ? <><i className="fa-solid fa-hourglass-half"></i> Avvio...</>
            : <><i className="fa-solid fa-magnifying-glass"></i> Analizza e compila</>}
        </button>
      </div>
      <div style={{ marginTop: 10, fontSize: 12, color: '#fff', fontWeight: 600 }}>
        Lingue da generare:
      </div>
      <div style={css.autofillLangPills}>
        {['IT', 'EN', 'DE', 'FR', 'ES', 'NL', 'PT'].map(code => (
          <span
            key={code}
            style={langPillStyle(autofillLangs.includes(code))}
            onClick={() => !startJobMutation.isPending && !startJobMutation.isSuccess && toggleAutofillLang(code)}
          >
            {code}
          </span>
        ))}
      </div>
      {/* Modalità manuale: incolla il testo del sito */}
      <div style={{ marginTop: 10 }}>
        <button
          style={{ background: 'none', border: 'none', color: BLUE_LIGHT, fontSize: 12, cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
          onClick={() => setAutofillManual(v => !v)}
        >
          {autofillManual ? '▲ Nascondi modalità manuale' : '▼ Il server non riesce a raggiungere il sito? Incolla il testo manualmente'}
        </button>
      </div>
      {autofillManual && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, color: BLUE_LIGHT, marginBottom: 4 }}>
            Vai sul sito dell'hotel, seleziona tutto il testo (Ctrl+A → Ctrl+C) e incollalo qui sotto.
            Oppure copia il testo della homepage e delle pagine camere/servizi.
          </div>
          <textarea
            style={{ width: '100%', minHeight: 120, fontSize: 12, padding: 8, border: `1px solid ${BLUE_MID}`, borderRadius: 6, resize: 'vertical', boxSizing: 'border-box' }}
            placeholder="Incolla qui il contenuto del sito web dell'hotel..."
            value={autofillContent}
            onChange={e => setAutofillContent(e.target.value)}
            disabled={startJobMutation.isPending || startJobMutation.isSuccess}
          />
        </div>
      )}
      {startJobMutation.isSuccess && (
        <div style={{ marginTop: 10, fontSize: 12, color: BLUE_DARK, background: BLUE_LIGHT, border: `1px solid ${BLUE_MID}`, borderRadius: 6, padding: '8px 12px' }}>
          <i className="fa-solid fa-hourglass-half"></i> Elaborazione in corso in background — puoi cambiare scheda liberamente.
          Riceverai una notifica in questa pagina quando il brief sarà pronto.
        </div>
      )}
      {autofillSuccess && (
        <div style={css.autofillSuccessBox}>
          <i className="fa-solid fa-circle-check"></i> Campi compilati con successo! Scorri il form per rivedere e correggere i dati generati.
        </div>
      )}
    </div>
  )

  return (
    <>
      {/* ── Auto-fill Panel ── */}
      {hasExistingBrief && !showNewScan ? (
        /* ── Compact "cached data" box ── */
        <div style={{
          background: BLUE_LIGHT, border: `1px solid ${BLUE_MID}`,
          borderRadius: T.radiusLg, padding: '16px 20px', marginBottom: 24,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <i className="fa-solid fa-circle-check" style={{ color: T.success, fontSize: 16 }}></i>
            <span style={{ fontWeight: 700, fontSize: 14, color: BLUE_DARK }}>
              Dati già scansionati
            </span>
          </div>
          <div style={{ fontSize: 13, color: BLUE_DARK, marginBottom: 12 }}>
            Il brief contiene già i dati di una scansione precedente. Puoi modificare i campi
            direttamente oppure eseguire una nuova scansione per sovrascriverli.
          </div>
          <button
            style={{
              background: BLUE, color: '#fff', border: 'none',
              padding: '8px 18px', borderRadius: T.radiusSm, cursor: 'pointer',
              fontWeight: 600, fontSize: 13,
            }}
            onClick={() => setShowNewScan(true)}
          >
            <i className="fa-solid fa-rotate"></i> Effettua nuova scansione
          </button>
        </div>
      ) : (
        <>
          {scanPanel}
          {hasExistingBrief && showNewScan && (
            <div style={{ textAlign: 'right', marginTop: -16, marginBottom: 16 }}>
              <button
                style={{ background: 'none', border: 'none', color: BLUE, fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}
                onClick={() => setShowNewScan(false)}
              >
                ← Annulla, usa i dati esistenti
              </button>
            </div>
          )}
        </>
      )}

      <div style={css.section}>
        <div style={css.sectionTitle}>Informazioni Progetto</div>
        <div style={css.grid2}>
          <div style={css.field}>
            <label style={css.label}>Nome progetto *</label>
            <input
              style={css.input}
              value={form.project_name}
              onChange={e => setField('project_name', e.target.value)}
              placeholder="es. Hotel Bella Vista — Search 2024"
            />
          </div>
          <div style={css.field}>
            <label style={css.label}>Google Ads Customer ID</label>
            <span style={css.hint}>Formato: 123-456-7890</span>
            <input
              style={css.input}
              value={form.google_ads_customer_id}
              onChange={e => setField('google_ads_customer_id', e.target.value)}
              placeholder="123-456-7890"
            />
          </div>
        </div>
      </div>
    </>
  )
}
