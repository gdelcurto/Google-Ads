import React from 'react'
import { T } from '../../styles/theme'

export const css: Record<string, React.CSSProperties> = {
  stepBubble: {
    width: 28, height: 28, borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 13, fontWeight: 700, flexShrink: 0,
  },
  stepLine: { flex: 1, height: 2, marginBottom: 16, marginLeft: 4, marginRight: 4 },
  stepLabel: { fontSize: 11, marginTop: 4, textAlign: 'center' },
  section: {
    background: T.bgCard, borderRadius: T.radiusLg, padding: 24,
    boxShadow: T.shadow, marginBottom: 16, border: `1px solid ${T.borderLight}`,
  },
  sectionTitle: {
    fontWeight: 700, fontSize: 15, color: T.text,
    marginBottom: 16, paddingBottom: 8, borderBottom: `1px solid ${T.borderLight}`,
  },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 },
  field: { marginBottom: 16 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 4 },
  hint: { display: 'block', fontSize: 11, color: T.textGray, marginBottom: 4 },
  input: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 14, boxSizing: 'border-box',
    background: T.bgCard, color: T.text,
  },
  inputErr: { borderColor: '#fca5a5' },
  select: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 14, background: T.bgCard, boxSizing: 'border-box',
    color: T.text,
  },
  textarea: {
    width: '100%', padding: '8px 10px', border: `1px solid ${T.border}`,
    borderRadius: T.radiusSm, fontSize: 13, fontFamily: 'inherit',
    resize: 'vertical', boxSizing: 'border-box', color: T.text,
  },
  charCount: { fontSize: 11, color: T.textGray, textAlign: 'right', marginTop: 2 },
  langCard: {
    border: `1px solid ${T.borderLight}`, borderRadius: T.radiusLg,
    padding: 16, marginBottom: 16, background: T.bgMuted,
  },
  langHeader: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: 12,
  },
  nav: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginTop: 24,
  },
  btn: {
    background: T.primary, color: '#fff', border: 'none',
    padding: '10px 24px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnGhost: {
    background: T.bgPage, color: T.text, border: `1px solid ${T.border}`,
    padding: '10px 24px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnGreen: {
    background: T.success, color: '#fff', border: 'none',
    padding: '10px 24px', borderRadius: T.radiusSm, cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  btnRed: {
    background: 'transparent', color: T.error, border: '1px solid #fca5a5',
    padding: '4px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
  },
  btnAdd: {
    background: 'transparent', color: T.primary, border: `1px solid ${T.primary}`,
    padding: '8px 16px', borderRadius: T.radiusSm, cursor: 'pointer', fontSize: 13, fontWeight: 600,
  },
  errBox: {
    background: '#fff0f0', border: '1px solid #fca5a5', padding: '12px 14px',
    borderRadius: T.radiusSm, fontSize: 13, color: T.error, marginBottom: 16,
  },
  successBox: {
    background: '#f0fdf4', border: '1px solid #86efac', padding: '12px 14px',
    borderRadius: T.radiusSm, fontSize: 13, color: '#166534', marginBottom: 16,
  },
  reviewCode: {
    background: T.bgPage, border: `1px solid ${T.border}`, borderRadius: T.radiusSm,
    padding: 16, fontSize: 12, fontFamily: 'monospace',
    overflowX: 'auto', whiteSpace: 'pre-wrap', maxHeight: 500, overflowY: 'auto',
  },
  autofillPanel: {
    background: '#e10098',
    border: 'none', borderRadius: T.radiusLg,
    padding: 20, marginBottom: 24,
  },
  autofillTitle: {
    fontWeight: 700, fontSize: 15, color: '#fff',
    marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8,
  },
  autofillSubtitle: { fontSize: 12, color: 'rgba(255,255,255,0.85)', marginBottom: 14 },
  autofillRow: { display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' as const },
  autofillUrlInput: {
    flex: 1, minWidth: 220, padding: '9px 12px',
    border: `1px solid ${T.border}`, borderRadius: T.radiusSm, fontSize: 14,
    boxSizing: 'border-box' as const, background: T.bgPage,
  },
  autofillLangPills: { display: 'flex', gap: 6, flexWrap: 'wrap' as const, marginTop: 10 },
  btnAutofill: {
    background: '#fff', color: '#e10098', border: 'none',
    padding: '9px 20px', borderRadius: T.radiusSm, cursor: 'pointer',
    fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap' as const,
  },
  autofillSuccessBox: {
    background: '#f0fdf4', border: '1px solid #86efac', padding: '10px 14px',
    borderRadius: T.radiusSm, fontSize: 13, color: '#166534', marginTop: 10,
  },
}

export const langPillStyle = (active: boolean): React.CSSProperties => ({
  padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
  cursor: 'pointer', border: active ? `2px solid ${T.primary}` : `1px solid ${T.border}`,
  background: active ? T.primary : T.bgCard, color: active ? '#fff' : T.textGray,
})
