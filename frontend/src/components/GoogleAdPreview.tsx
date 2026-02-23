import React from 'react'
import { T } from '../styles/theme'

export interface AdPreviewLang {
  code?: string
  name?: string
  headlines: string[]
  descriptions: string[]
  callouts: string[]
  sitelinks: { text: string; description_1: string; description_2: string; final_url: string }[]
}

function charCountStyle(val: number, max: number): React.CSSProperties {
  return { fontSize: 11, color: val > max ? '#dc2626' : '#9ca3af', marginLeft: 4 }
}

const AD_GREEN  = '#188038'
const AD_BLUE   = '#1a0dab'
const AD_GRAY   = '#4d5156'
const AD_BORDER = '#e0e0e0'

/** Generate distinct 3-headline combos from the pool (deterministic, no randomness). */
function headlineCombos(headlines: string[], maxCombos = 4): string[][] {
  if (headlines.length <= 3) return [headlines.slice(0, 3)]
  const combos: string[][] = []
  const n = headlines.length

  // Combo 1: first 3
  combos.push(headlines.slice(0, 3))

  // Combo 2: next 3 (or wrap)
  if (n >= 6) combos.push(headlines.slice(3, 6))
  else if (n > 3) combos.push([headlines[0], headlines[Math.floor(n / 2)], headlines[n - 1]])

  // Combo 3: spaced pick (0, ~1/3, ~2/3)
  if (n >= 5) {
    const c = [headlines[1], headlines[Math.floor(n / 3)], headlines[Math.floor(2 * n / 3)]]
    if (!combos.some(ex => ex.join('|') === c.join('|'))) combos.push(c)
  }

  // Combo 4: last 3
  if (n >= 7) {
    const c = headlines.slice(n - 3)
    if (!combos.some(ex => ex.join('|') === c.join('|'))) combos.push(c)
  }

  return combos.slice(0, maxCombos)
}

/** Single SERP card with given 3 headlines + 2 descriptions */
function SerpCard({ displayH, displayD, callouts, sitelinks, domain }: {
  displayH: string[]; displayD: string[]; callouts: string[]; sitelinks: AdPreviewLang['sitelinks']; domain: string
}) {
  return (
    <div style={{
      fontFamily: 'Arial, sans-serif',
      background: '#fff',
      border: `1px solid ${AD_BORDER}`,
      borderRadius: 8,
      padding: '16px 20px',
    }}>
      {/* Ad badge + URL breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <span style={{
          border: `1px solid ${AD_GREEN}`, color: AD_GREEN,
          borderRadius: 3, fontSize: 11, padding: '1px 5px', fontWeight: 700, letterSpacing: 0.3,
        }}>
          Annuncio
        </span>
        <span style={{ color: '#202124', fontSize: 13 }}>{domain}</span>
      </div>

      {/* Headlines */}
      <div style={{ color: AD_BLUE, fontSize: 20, fontWeight: 400, marginBottom: 6, lineHeight: 1.35 }}>
        {displayH.length > 0
          ? displayH.join(' | ')
          : <span style={{ color: '#d1d5db', fontStyle: 'italic' }}>Headline non ancora inserite</span>
        }
      </div>

      {/* Descriptions */}
      <div style={{ color: AD_GRAY, fontSize: 14, lineHeight: 1.55 }}>
        {displayD.length > 0
          ? displayD.join(' ')
          : <span style={{ color: '#d1d5db', fontStyle: 'italic' }}>Descrizioni non ancora inserite</span>
        }
      </div>

      {/* Sitelinks */}
      {sitelinks.length > 0 && (
        <div style={{
          marginTop: 12, borderTop: `1px solid ${AD_BORDER}`, paddingTop: 12,
          display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px 24px',
        }}>
          {sitelinks.slice(0, 4).map((sl, j) => (
            <div key={j}>
              <div style={{ color: AD_BLUE, fontSize: 14, fontWeight: 500 }}>{sl.text}</div>
              <div style={{ color: AD_GRAY, fontSize: 12, marginTop: 2 }}>{sl.description_1}</div>
            </div>
          ))}
        </div>
      )}

      {/* Callouts */}
      {callouts.length > 0 && (
        <div style={{ marginTop: 10, color: AD_GRAY, fontSize: 13 }}>
          {callouts.slice(0, 6).join(' \u00B7 ')}
        </div>
      )}
    </div>
  )
}

/**
 * Multiple SERP previews stacked — shows different headline combinations.
 * Used on the left side of the 55/45 layout.
 */
export function GoogleAdSerpPreview({ lang, domain }: { lang: AdPreviewLang; domain?: string }) {
  const { headlines, descriptions, callouts, sitelinks } = lang
  const displayD = descriptions.slice(0, 2)
  const displayDomain = domain || 'www.hotel.com'
  const combos = headlineCombos(headlines)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {combos.map((combo, idx) => (
        <div key={idx}>
          {combos.length > 1 && (
            <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 4, fontWeight: 600 }}>
              Combinazione {idx + 1}
            </div>
          )}
          <SerpCard
            displayH={combo}
            displayD={displayD}
            callouts={callouts}
            sitelinks={sitelinks}
            domain={displayDomain}
          />
        </div>
      ))}
    </div>
  )
}

/**
 * Asset inspector panel — headline/description/sitelink list with char counts.
 * Displayed once at campaign level when assets are shared across ad groups.
 */
export function AssetInspector({ lang }: { lang: AdPreviewLang }) {
  const { headlines, descriptions, sitelinks, callouts } = lang

  return (
    <div style={{ fontSize: 12, color: T.textGray }}>
      <div style={{ fontWeight: 700, color: T.text, marginBottom: 10, fontSize: 13 }}>Asset completi</div>

      {/* Asset count bar */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 14, fontSize: 12, color: '#6b7280', flexWrap: 'wrap' as const }}>
        <span>
          Headline: <strong style={{ color: headlines.length >= 3 ? T.success : T.warning }}>
            {headlines.length}
          </strong>/15
        </span>
        <span>
          Descrizioni: <strong style={{ color: descriptions.length >= 2 ? T.success : T.warning }}>
            {descriptions.length}
          </strong>/4
        </span>
        <span>
          Sitelink: <strong style={{ color: sitelinks.length >= 2 ? T.success : T.warning }}>
            {sitelinks.length}
          </strong>
        </span>
        <span>
          Callout: <strong style={{ color: callouts.length >= 2 ? T.success : '#6b7280' }}>
            {callouts.length}
          </strong>
        </span>
      </div>

      {sitelinks.length < 2 && (
        <div style={{ marginBottom: 10, color: T.warning, fontSize: 13 }}>
          Aggiungi almeno 2 sitelink per questa lingua.
        </div>
      )}

      {/* Headlines list */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 600, color: T.text, marginBottom: 4, fontSize: 12 }}>
          Headline ({headlines.length})
        </div>
        {headlines.length === 0
          ? <div style={{ fontStyle: 'italic' }}>Nessuna</div>
          : headlines.map((h, i) => (
            <div key={i} style={{ padding: '3px 0', borderBottom: `1px solid ${T.borderLight}` }}>
              {h}
              <span style={charCountStyle(h.length, 30)}>{h.length}/30</span>
            </div>
          ))
        }
      </div>

      {/* Descriptions list */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 600, color: T.text, marginBottom: 4, fontSize: 12 }}>
          Descrizioni ({descriptions.length})
        </div>
        {descriptions.length === 0
          ? <div style={{ fontStyle: 'italic' }}>Nessuna</div>
          : descriptions.map((d, i) => (
            <div key={i} style={{ padding: '3px 0', borderBottom: `1px solid ${T.borderLight}` }}>
              {d}
              <span style={charCountStyle(d.length, 90)}>{d.length}/90</span>
            </div>
          ))
        }
      </div>

      {/* Sitelinks list */}
      <div>
        <div style={{ fontWeight: 600, color: T.text, marginBottom: 4, fontSize: 12 }}>
          Sitelink ({sitelinks.length})
        </div>
        {sitelinks.length === 0
          ? <div style={{ fontStyle: 'italic', color: T.warning }}>Nessuno — generali con AI</div>
          : sitelinks.map((sl, i) => (
            <div key={i} style={{ padding: '4px 0', borderBottom: `1px solid ${T.borderLight}` }}>
              <div style={{ fontWeight: 600 }}>
                {sl.text}
                <span style={charCountStyle(sl.text.length, 25)}>{sl.text.length}/25</span>
              </div>
              <div style={{ color: '#9ca3af', marginTop: 1 }}>{sl.description_1}</div>
              <div style={{ color: '#9ca3af' }}>{sl.description_2}</div>
            </div>
          ))
        }
      </div>
    </div>
  )
}

/**
 * Full Google Ad Preview — SERP mockup + asset inspector side-by-side.
 * Kept for backward compatibility, used when a single ad group is displayed standalone.
 */
export function GoogleAdPreview({ lang, domain }: { lang: AdPreviewLang; domain?: string }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 28, alignItems: 'start' }}>
      <div>
        <GoogleAdSerpPreview lang={lang} domain={domain} />
        {/* Asset count bar */}
        <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 12, color: '#6b7280', flexWrap: 'wrap' as const }}>
          <span>
            Headline: <strong style={{ color: lang.headlines.length >= 3 ? T.success : T.warning }}>
              {lang.headlines.length}
            </strong>/15
          </span>
          <span>
            Descrizioni: <strong style={{ color: lang.descriptions.length >= 2 ? T.success : T.warning }}>
              {lang.descriptions.length}
            </strong>/4
          </span>
          <span>
            Sitelink: <strong style={{ color: lang.sitelinks.length >= 2 ? T.success : T.warning }}>
              {lang.sitelinks.length}
            </strong>
          </span>
          <span>
            Callout: <strong style={{ color: lang.callouts.length >= 2 ? T.success : '#6b7280' }}>
              {lang.callouts.length}
            </strong>
          </span>
        </div>
        {lang.sitelinks.length < 2 && (
          <div style={{ marginTop: 8, color: T.warning, fontSize: 13 }}>
            Aggiungi almeno 2 sitelink per questa lingua.
          </div>
        )}
      </div>
      <AssetInspector lang={lang} />
    </div>
  )
}
