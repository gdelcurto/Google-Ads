import { FormState, RemarketingListState } from '../types'
import { css } from '../styles'
import { T } from '../../../styles/theme'

interface Props {
  form: FormState
  setField: (key: keyof FormState, val: string) => void
  remarketingLists: RemarketingListState[]
  addRemarketingList: () => void
  removeRemarketingList: (idx: number) => void
  setRemarketingListField: (idx: number, key: keyof RemarketingListState, val: string) => void
  selectedTypes: Set<string>
}

export function Step3Hotel({
  form, setField, remarketingLists, addRemarketingList, removeRemarketingList, setRemarketingListField, selectedTypes,
}: Props) {
  return (
    <>
      <div style={css.section}>
        <div style={css.sectionTitle}>Specifiche Hotel</div>
        <div style={css.grid2}>
          <div style={css.field}>
            <label style={css.label}>Categoria struttura *</label>
            <select style={css.select} value={form.hotel_category} onChange={e => setField('hotel_category', e.target.value)}>
              <option value="city_hotel">City Hotel</option>
              <option value="resort">Resort</option>
              <option value="boutique">Boutique</option>
              <option value="business">Business</option>
              <option value="agriturismo">Agriturismo</option>
            </select>
          </div>
          <div style={css.field}>
            <label style={css.label}>Stelle (1–5) *</label>
            <input
              style={css.input}
              type="number"
              min="1"
              max="5"
              value={form.stars}
              onChange={e => setField('stars', e.target.value)}
            />
          </div>
          <div style={css.field}>
            <label style={css.label}>Numero camere</label>
            <input
              style={css.input}
              type="number"
              min="1"
              value={form.rooms}
              onChange={e => setField('rooms', e.target.value)}
              placeholder="es. 80"
            />
          </div>
          <div style={css.field}>
            <label style={css.label}>URL Booking Engine *</label>
            <input
              style={css.input}
              value={form.booking_engine_url}
              onChange={e => setField('booking_engine_url', e.target.value)}
              placeholder="https://booking.hotel.it/it"
            />
          </div>
        </div>
        <div style={css.field}>
          <label style={css.label}>Indirizzo completo *</label>
          <input
            style={css.input}
            value={form.address}
            onChange={e => setField('address', e.target.value)}
            placeholder="Via Roma 1, 00100 Roma, Italia"
          />
        </div>
        <div style={css.grid2}>
          <div style={css.field}>
            <label style={css.label}>Servizi offerti (uno per riga)</label>
            <textarea
              style={{ ...css.textarea, minHeight: 110 }}
              value={form.services}
              onChange={e => setField('services', e.target.value)}
              placeholder={'Piscina esterna\nSPA e centro benessere\nRistorante gourmet\nSala conferenze\nBar'}
            />
          </div>
          <div style={css.field}>
            <label style={css.label}>Punti di forza (uno per riga)</label>
            <textarea
              style={{ ...css.textarea, minHeight: 110 }}
              value={form.strengths}
              onChange={e => setField('strengths', e.target.value)}
              placeholder={'Vista panoramica sul mare\nPosizione centrale\nPersonale multilingue\nFamiglie benvenute'}
            />
          </div>
        </div>
      </div>

      <div style={css.section}>
        <div style={css.sectionTitle}>Targeting Geografico</div>
        <div style={css.grid2}>
          <div style={css.field}>
            <label style={css.label}>Paesi target (codice ISO 2, uno per riga)</label>
            <textarea
              style={{ ...css.textarea, minHeight: 90 }}
              value={form.target_countries}
              onChange={e => setField('target_countries', e.target.value)}
              placeholder={'IT\nDE\nFR\nGB'}
            />
          </div>
          <div style={css.field}>
            <label style={css.label}>Città target (una per riga — opzionale)</label>
            <textarea
              style={{ ...css.textarea, minHeight: 90 }}
              value={form.target_cities}
              onChange={e => setField('target_cities', e.target.value)}
              placeholder={'Milano\nRoma\nTorino'}
            />
          </div>
        </div>
      </div>

      <div style={css.section}>
        <div style={css.sectionTitle}>Audience & Remarketing</div>
        <p style={{ fontSize: 12, color: T.textGray, marginBottom: 12 }}>
          Obbligatorio se hai selezionato campagne <strong>Retargeting</strong> o <strong>Demand Gen</strong>.
          {!selectedTypes.has('retargeting') && !selectedTypes.has('demand_gen') && ' (non attive al momento)'}
          {' '}Inserisci le audience list già create in Google Ads.
        </p>
        {remarketingLists.map((rl, idx) => (
          <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1fr 160px 70px 1fr auto', gap: 8, marginBottom: 8, alignItems: 'flex-end' }}>
            <div>
              <label style={{ ...css.label, fontSize: 11 }}>Nome lista *</label>
              <input style={css.input} value={rl.name} onChange={e => setRemarketingListField(idx, 'name', e.target.value)} placeholder="All Website Visitors" />
            </div>
            <div>
              <label style={{ ...css.label, fontSize: 11 }}>Tipo</label>
              <select style={css.select} value={rl.type} onChange={e => setRemarketingListField(idx, 'type', e.target.value)}>
                <option value="website_visitors">Visitatori sito</option>
                <option value="customer_list">Customer list</option>
                <option value="youtube">YouTube</option>
              </select>
            </div>
            <div>
              <label style={{ ...css.label, fontSize: 11 }}>Giorni</label>
              <input style={css.input} type="number" min="1" max="540" value={rl.lookback_days} onChange={e => setRemarketingListField(idx, 'lookback_days', e.target.value)} placeholder="30" />
            </div>
            <div>
              <label style={{ ...css.label, fontSize: 11 }}>Sorgente (URL o nome)</label>
              <input style={css.input} value={rl.source} onChange={e => setRemarketingListField(idx, 'source', e.target.value)} placeholder="https://www.hotel.it" />
            </div>
            <button style={{ ...css.btnRed, alignSelf: 'flex-end', marginBottom: 0 }} onClick={() => removeRemarketingList(idx)}><i className="fa-solid fa-xmark"></i></button>
          </div>
        ))}
        <button style={css.btnAdd} onClick={addRemarketingList}>+ Aggiungi audience list</button>
      </div>
    </>
  )
}
