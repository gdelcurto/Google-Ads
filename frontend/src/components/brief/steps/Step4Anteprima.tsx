import { FormState, LangState } from '../types'
import { css } from '../styles'
import { T } from '../../../styles/theme'
import { toLines } from '../utils'
import { GoogleAdPreview } from '../../GoogleAdPreview'

interface Props {
  form: FormState
  langs: LangState[]
  previewLangIdx: number
  setPreviewLangIdx: (i: number) => void
}

export function Step4Anteprima({ form, langs, previewLangIdx, setPreviewLangIdx }: Props) {
  return (
    <div style={css.section}>
      <div style={css.sectionTitle}>Anteprima Google Ads</div>
      <p style={{ fontSize: 13, color: T.textGray, marginBottom: 16 }}>
        Simulazione di come apparirà il tuo annuncio su Google. Google seleziona automaticamente
        la combinazione di headline e descrizioni più performante.
      </p>
      {/* Language tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' as const }}>
        {langs.map((lang, i) => (
          <button
            key={i}
            style={{
              padding: '6px 16px', border: 'none', borderRadius: 20, cursor: 'pointer',
              fontSize: 13, fontWeight: previewLangIdx === i ? 600 : 400,
              background: previewLangIdx === i ? T.primary : T.bgPage,
              color: previewLangIdx === i ? '#fff' : T.textGray,
              transition: 'all .15s',
            }}
            onClick={() => setPreviewLangIdx(i)}
          >
            {lang.code || `Lingua ${i + 1}`}
            {lang.name ? ` — ${lang.name}` : ''}
          </button>
        ))}
      </div>
      {langs[previewLangIdx] && (() => {
        const l = langs[previewLangIdx]
        return (
          <GoogleAdPreview
            lang={{
              headlines: toLines(l.headlines),
              descriptions: toLines(l.descriptions),
              callouts: toLines(l.callouts),
              sitelinks: l.sitelinks,
            }}
            domain={form.domain || (l.landing_page ? (() => { try { return new URL(l.landing_page).hostname } catch { return '' } })() : '')}
          />
        )
      })()}
    </div>
  )
}
