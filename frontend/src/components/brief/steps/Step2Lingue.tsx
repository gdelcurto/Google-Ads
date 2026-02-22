import { useState } from 'react'
import { LangState, SitelinkState } from '../types'
import { css } from '../styles'
import { T } from '../../../styles/theme'
import { toLines } from '../utils'

// ── PerTypeCopySection ─────────────────────────────────────────────────────────

function PerTypeCopySection({
  label, description,
  headlinesValue, descriptionsValue,
  headlinesPlaceholder, descriptionsPlaceholder,
  onHeadlinesChange, onDescriptionsChange,
}: {
  label: string
  description: string
  headlinesValue: string
  descriptionsValue: string
  headlinesPlaceholder: string
  descriptionsPlaceholder: string
  onHeadlinesChange: (v: string) => void
  onDescriptionsChange: (v: string) => void
}) {
  const [open, setOpen] = useState(false)
  const hasContent = headlinesValue.trim().length > 0 || descriptionsValue.trim().length > 0

  return (
    <div style={{ border: `1px solid ${hasContent ? T.primary : T.borderLight}`, borderRadius: T.radiusSm, marginBottom: 10 }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', padding: '10px 14px',
          background: hasContent ? '#eff6ff' : T.bgPage,
          border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderRadius: T.radiusSm,
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 13, color: hasContent ? T.primary : T.textGray }}>
          {hasContent ? '✓ ' : ''}{label}
          {!hasContent && <span style={{ fontWeight: 400, fontSize: 11, marginLeft: 8, color: T.textGray }}>(opzionale)</span>}
        </span>
        <span style={{ fontSize: 11, color: T.textGray }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={{ padding: '14px 14px 10px', borderTop: `1px solid ${T.borderLight}` }}>
          <p style={{ fontSize: 12, color: T.textGray, marginBottom: 12, marginTop: 0 }}>{description}</p>

          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: T.text, display: 'block', marginBottom: 4 }}>
              Headline dedicate (una per riga — max 30 car.)
            </label>
            <textarea
              style={{ width: '100%', fontFamily: 'inherit', fontSize: 13, padding: '8px 10px', border: `1px solid ${T.border}`, borderRadius: T.radiusSm, minHeight: 90, resize: 'vertical', boxSizing: 'border-box' as const }}
              value={headlinesValue}
              onChange={e => onHeadlinesChange(e.target.value)}
              placeholder={headlinesPlaceholder}
            />
            {toLines(headlinesValue).map((h, j) => h.length > 30 && (
              <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                Riga {j + 1} troppo lunga ({h.length}/30)
              </div>
            ))}
            <div style={{ fontSize: 11, color: T.textGray, textAlign: 'right', marginTop: 2 }}>
              {toLines(headlinesValue).length} headline
            </div>
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: T.text, display: 'block', marginBottom: 4 }}>
              Descrizioni dedicate (una per riga — max 90 car.)
            </label>
            <textarea
              style={{ width: '100%', fontFamily: 'inherit', fontSize: 13, padding: '8px 10px', border: `1px solid ${T.border}`, borderRadius: T.radiusSm, minHeight: 70, resize: 'vertical', boxSizing: 'border-box' as const }}
              value={descriptionsValue}
              onChange={e => onDescriptionsChange(e.target.value)}
              placeholder={descriptionsPlaceholder}
            />
            {toLines(descriptionsValue).map((d, j) => d.length > 90 && (
              <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                Riga {j + 1} troppo lunga ({d.length}/90)
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Step2Lingue ────────────────────────────────────────────────────────────────

interface Props {
  brandName: string
  langs: LangState[]
  setLangField: (i: number, key: keyof LangState, val: string) => void
  handleLangCode: (i: number, code: string) => void
  addLang: () => void
  removeLang: (i: number) => void
  addSitelink: (langIdx: number) => void
  removeSitelink: (langIdx: number, slIdx: number) => void
  setSitelinkField: (langIdx: number, slIdx: number, key: keyof SitelinkState, val: string) => void
  slSuggestMutation: { mutate: (vars: { langIdx: number; lang: LangState }) => void }
  kwSuggestMutation: { mutate: (vars: { langIdx: number; lang: LangState }) => void }
  slSuggestingLang: number | null
  kwSuggestingLang: number | null
  setSlSuggestingLang: (v: number | null) => void
  setKwSuggestingLang: (v: number | null) => void
  setErrors: (errs: string[]) => void
}

export function Step2Lingue({
  brandName, langs, setLangField, handleLangCode, addLang, removeLang,
  addSitelink, removeSitelink, setSitelinkField,
  slSuggestMutation, kwSuggestMutation,
  slSuggestingLang, kwSuggestingLang, setSlSuggestingLang, setKwSuggestingLang,
  setErrors,
}: Props) {
  return (
    <div>
      {langs.map((lang, i) => (
        <div key={i} style={css.langCard}>
          <div style={css.langHeader}>
            <strong style={{ fontSize: 15 }}>
              Lingua {i + 1}{lang.code ? ` — ${lang.code}` : ''}
              {lang.name ? ` (${lang.name})` : ''}
            </strong>
            {langs.length > 1 && (
              <button style={css.btnRed} onClick={() => removeLang(i)}><i className="fa-solid fa-xmark"></i> Rimuovi</button>
            )}
          </div>

          <div style={css.grid2}>
            <div style={css.field}>
              <label style={css.label}>Codice lingua *</label>
              <span style={css.hint}>IT, EN, DE, FR, ES, NL, PT…</span>
              <input
                style={css.input}
                value={lang.code}
                onChange={e => handleLangCode(i, e.target.value)}
                placeholder="IT"
                maxLength={5}
              />
            </div>
            <div style={css.field}>
              <label style={css.label}>Nome lingua *</label>
              <input
                style={css.input}
                value={lang.name}
                onChange={e => setLangField(i, 'name', e.target.value)}
                placeholder="Italiano"
              />
            </div>
            <div style={css.field}>
              <label style={css.label}>Google Language ID *</label>
              <span style={css.hint}>IT=1004, EN=1000, DE=1001, FR=1002, ES=1003</span>
              <input
                style={css.input}
                type="number"
                value={lang.google_language_id}
                onChange={e => setLangField(i, 'google_language_id', e.target.value)}
                placeholder="1004"
              />
            </div>
            <div style={css.field}>
              <label style={css.label}>Landing Page URL *</label>
              <input
                style={css.input}
                value={lang.landing_page}
                onChange={e => setLangField(i, 'landing_page', e.target.value)}
                placeholder="https://www.hotel.it/"
              />
            </div>
          </div>

          <div style={css.field}>
            <label style={css.label}>Brand Terms * (uno per riga)</label>
            <span style={css.hint}>Varianti del nome brand da targettizzare nelle campagne brand</span>
            <textarea
              style={{ ...css.textarea, minHeight: 80 }}
              value={lang.brand_terms}
              onChange={e => setLangField(i, 'brand_terms', e.target.value)}
              placeholder={'Hotel Bella Vista\nBella Vista Hotel\nHBV'}
            />
          </div>

          <div style={css.field}>
            <label style={css.label}>USP principale (opzionale)</label>
            <span style={css.hint}>Proposta di valore unica — max 90 caratteri</span>
            <input
              style={{ ...css.input, ...(lang.usp_main.length > 90 ? css.inputErr : {}) }}
              value={lang.usp_main}
              onChange={e => setLangField(i, 'usp_main', e.target.value)}
              placeholder="es. Prenota diretto e risparmia fino al 20%"
            />
            <div style={css.charCount}>{lang.usp_main.length} / 90</div>
          </div>

          <div style={css.field}>
            <label style={css.label}>Headline RSA * (una per riga — min 3, max 30 caratteri ciascuna)</label>
            <textarea
              style={{ ...css.textarea, minHeight: 130 }}
              value={lang.headlines}
              onChange={e => setLangField(i, 'headlines', e.target.value)}
              placeholder={'Hotel Bella Vista\nPrenota Diretto Online\nMiglior Tariffa Garantita\nVista Mare Panoramica\nPiscina Esterna Riscaldata'}
            />
            {toLines(lang.headlines).map((h, j) => h.length > 30 && (
              <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                Riga {j + 1} troppo lunga ({h.length}/30): "{h.slice(0, 25)}..."
              </div>
            ))}
            <div style={css.charCount}>{toLines(lang.headlines).length} headline</div>
          </div>

          <div style={css.field}>
            <label style={css.label}>Descrizioni RSA * (una per riga — min 2, max 90 caratteri ciascuna)</label>
            <textarea
              style={{ ...css.textarea, minHeight: 100 }}
              value={lang.descriptions}
              onChange={e => setLangField(i, 'descriptions', e.target.value)}
              placeholder={'Prenota sul sito ufficiale per la migliore tariffa garantita e disdici gratis.\nCamera Superior con vista mare e colazione inclusa, posizione centrale.'}
            />
            {toLines(lang.descriptions).map((d, j) => d.length > 90 && (
              <div key={j} style={{ fontSize: 11, color: '#dc2626' }}>
                Riga {j + 1} troppo lunga ({d.length}/90)
              </div>
            ))}
            <div style={css.charCount}>{toLines(lang.descriptions).length} descrizioni</div>
          </div>

          <div style={css.field}>
            <label style={css.label}>Callout (uno per riga — opzionale)</label>
            <textarea
              style={{ ...css.textarea, minHeight: 80 }}
              value={lang.callouts}
              onChange={e => setLangField(i, 'callouts', e.target.value)}
              placeholder={'Cancellazione gratuita\nWi-Fi incluso\nParcheggio gratuito\nCheck-in anticipato'}
            />
          </div>

          {/* ── Sitelinks ── */}
          <div style={css.field}>
            <label style={css.label}>Sitelink (consigliati min. 2)</label>
            <span style={css.hint}>Testo max 25 car. · Descrizioni max 35 car. ciascuna</span>
            <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'center', flexWrap: 'wrap' as const }}>
              <button
                style={{ ...css.btnAdd, fontSize: 12, padding: '6px 14px', opacity: slSuggestingLang === i ? 0.6 : 1 }}
                onClick={() => {
                  if (!brandName) { setErrors(['Inserisci prima il nome del brand (Step 0)']); return }
                  setSlSuggestingLang(i)
                  slSuggestMutation.mutate({ langIdx: i, lang })
                }}
                disabled={slSuggestingLang === i}
              >
                {slSuggestingLang === i
                  ? <><i className="fa-solid fa-hourglass-half"></i> Generando sitelink...</>
                  : <><i className="fa-solid fa-wand-magic-sparkles"></i> Genera sitelink con AI</>}
              </button>
              <span style={{ fontSize: 11, color: T.textGray }}>oppure aggiungili manualmente →</span>
            </div>
            {lang.sitelinks.map((sl, j) => (
              <div key={j} style={{ border: `1px solid ${T.borderLight}`, borderRadius: 6, padding: 10, marginBottom: 8, background: T.bgPage }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <strong style={{ fontSize: 12, color: T.textGray }}>Sitelink {j + 1}</strong>
                  <button style={css.btnRed} onClick={() => removeSitelink(i, j)}><i className="fa-solid fa-xmark"></i></button>
                </div>
                <div style={css.grid2}>
                  <div>
                    <label style={{ ...css.label, fontSize: 11 }}>Testo *</label>
                    <input style={css.input} value={sl.text} onChange={e => setSitelinkField(i, j, 'text', e.target.value)} maxLength={25} placeholder="Prenota Ora" />
                    <div style={css.charCount}>{sl.text.length}/25</div>
                  </div>
                  <div>
                    <label style={{ ...css.label, fontSize: 11 }}>URL finale *</label>
                    <input style={css.input} value={sl.final_url} onChange={e => setSitelinkField(i, j, 'final_url', e.target.value)} placeholder="https://..." />
                  </div>
                  <div>
                    <label style={{ ...css.label, fontSize: 11 }}>Descrizione 1</label>
                    <input style={css.input} value={sl.description_1} onChange={e => setSitelinkField(i, j, 'description_1', e.target.value)} maxLength={35} placeholder="Miglior tariffa garantita" />
                    <div style={css.charCount}>{sl.description_1.length}/35</div>
                  </div>
                  <div>
                    <label style={{ ...css.label, fontSize: 11 }}>Descrizione 2</label>
                    <input style={css.input} value={sl.description_2} onChange={e => setSitelinkField(i, j, 'description_2', e.target.value)} maxLength={35} placeholder="Cancellazione gratuita" />
                    <div style={css.charCount}>{sl.description_2.length}/35</div>
                  </div>
                </div>
              </div>
            ))}
            <button style={css.btnAdd} onClick={() => addSitelink(i)}>+ Aggiungi sitelink</button>
          </div>

          {/* ── Acquisition Keywords ── */}
          <div style={css.field}>
            <label style={css.label}>Keyword Acquisition — opzionale</label>
            <span style={css.hint}>Formato: "tema: kw1, kw2, kw3" — una riga per tema. Usate nelle campagne Search Acquisition.</span>
            <div style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'center', flexWrap: 'wrap' as const }}>
              <button
                style={{ ...css.btnAdd, fontSize: 12, padding: '6px 14px', opacity: kwSuggestingLang === i ? 0.6 : 1 }}
                onClick={() => {
                  if (!brandName) { setErrors(['Inserisci prima il nome del brand (Step 0)']); return }
                  setKwSuggestingLang(i)
                  kwSuggestMutation.mutate({ langIdx: i, lang })
                }}
                disabled={kwSuggestingLang === i}
              >
                {kwSuggestingLang === i
                  ? <><i className="fa-solid fa-hourglass-half"></i> Generando keyword...</>
                  : <><i className="fa-solid fa-wand-magic-sparkles"></i> Genera keyword con AI</>}
              </button>
              <span style={{ fontSize: 11, color: T.textGray }}>oppure inseriscile manualmente ↓</span>
            </div>
            <textarea
              style={{ ...css.textarea, minHeight: 100 }}
              value={lang.kw_themes}
              onChange={e => setLangField(i, 'kw_themes', e.target.value)}
              placeholder={'prenotazione: prenota hotel X, hotel X booking\ncategoria: hotel 4 stelle Roma\nposizione: hotel centro storico Roma'}
            />
          </div>
          <div style={css.field}>
            <label style={css.label}>Keyword Negative — opzionale</label>
            <span style={css.hint}>Una per riga</span>
            <textarea
              style={{ ...css.textarea, minHeight: 70 }}
              value={lang.kw_negative}
              onChange={e => setLangField(i, 'kw_negative', e.target.value)}
              placeholder={'gratis\nreview\nopinioni\nfoto'}
            />
          </div>

          {/* ── Per-type RSA copy (optional) ── */}
          <PerTypeCopySection
            label="Copy Brand Search"
            description="Copy dedicata alle campagne Brand. Deve contenere il nome dell'hotel. Sostituisce gli headline generici per questo tipo di campagna."
            headlinesValue={lang.brand_headlines}
            descriptionsValue={lang.brand_descriptions}
            headlinesPlaceholder={'Hotel Bella Vista\nSito Ufficiale\nMiglior Tariffa Garantita\nPrenota Direttamente'}
            descriptionsPlaceholder={'Prenota sul sito ufficiale di Hotel Bella Vista e ottieni la miglior tariffa garantita.'}
            onHeadlinesChange={v => setLangField(i, 'brand_headlines', v)}
            onDescriptionsChange={v => setLangField(i, 'brand_descriptions', v)}
          />

          <PerTypeCopySection
            label="Copy Acquisition Search"
            description="Copy per campagne di acquisizione. NON deve contenere il brand — usa termini di categoria, posizione e USP generici."
            headlinesValue={lang.acquisition_headlines}
            descriptionsValue={lang.acquisition_descriptions}
            headlinesPlaceholder={'Hotel 4 Stelle Roma Centro\nColazione Inclusa\nPiscina Panoramica\nCancellazione Gratuita'}
            descriptionsPlaceholder={'Hotel 4 stelle nel cuore di Roma. Prenota online e risparmia fino al 20% sulla tariffa ufficiale.'}
            onHeadlinesChange={v => setLangField(i, 'acquisition_headlines', v)}
            onDescriptionsChange={v => setLangField(i, 'acquisition_descriptions', v)}
          />

          <PerTypeCopySection
            label="Copy Retargeting / Display"
            description="Copy urgency/personalizzata per visitatori che hanno già visto il sito. Usa messaggi di ritorno e offerte riservate."
            headlinesValue={lang.retargeting_headlines}
            descriptionsValue={lang.retargeting_descriptions}
            headlinesPlaceholder={'Completa la Prenotazione\nOfferta Riservata a Te\nUltimi Posti Disponibili\nTorna e Risparmia'}
            descriptionsPlaceholder={'Hai visitato il nostro sito? Completa la prenotazione oggi e approfitta di una tariffa esclusiva.'}
            onHeadlinesChange={v => setLangField(i, 'retargeting_headlines', v)}
            onDescriptionsChange={v => setLangField(i, 'retargeting_descriptions', v)}
          />
        </div>
      ))}
      <button style={css.btnAdd} onClick={addLang}>+ Aggiungi lingua</button>
    </div>
  )
}
