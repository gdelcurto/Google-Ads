import { FormState, LangState, TypeObjective, RemarketingListState } from '../types'
import { css } from '../styles'
import { T } from '../../../styles/theme'
import { buildBrief } from '../utils'

interface Props {
  form: FormState
  langs: LangState[]
  selectedTypes: Set<string>
  budgetByTypeLang: Record<string, Record<string, string>>
  remarketingLists: RemarketingListState[]
  objectivesByType: Record<string, TypeObjective>
}

export function Step5Revisione({ form, langs, selectedTypes, budgetByTypeLang, remarketingLists, objectivesByType }: Props) {
  return (
    <div style={css.section}>
      <div style={css.sectionTitle}>Revisione Brief</div>
      <p style={{ fontSize: 13, color: T.textGray, marginBottom: 12 }}>
        Controlla il JSON prima di salvare. Puoi tornare indietro per modificare i dati.
      </p>
      <div style={css.reviewCode}>
        {JSON.stringify(buildBrief(form, langs, selectedTypes, budgetByTypeLang, remarketingLists, objectivesByType), null, 2)}
      </div>
    </div>
  )
}
