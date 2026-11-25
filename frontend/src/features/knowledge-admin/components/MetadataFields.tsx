import { useTranslation } from 'react-i18next'
import type { RegulationMetadata } from '../api/ingestionApi'
import { REGULATION_TYPES, regulationType } from '../regulationTypes'
import { FieldLabel } from './FieldLabel'

/** The regulation's metadata, shared by "add a regulation" and "edit document". */
export type MetadataValues = Pick<RegulationMetadata,
  'regulation_type' | 'regulation_number' | 'title' | 'issuer' | 'topic' | 'issued_at' | 'effective_from' | 'effective_until'>

interface Props {
  value: MetadataValues
  onChange: (value: MetadataValues) => void
}

type DateKey = 'issued_at' | 'effective_from' | 'effective_until'

export function MetadataFields({ value, onChange }: Props) {
  const { t } = useTranslation()
  const set = <K extends keyof MetadataValues>(key: K, next: MetadataValues[K]) => onChange({ ...value, [key]: next })
  const setDate = (key: DateKey, next: string) => set(key, next || null)
  // The issuer follows the type (a PMK is issued by the Minister of Finance) unless the admin typed another one,
  // e.g. for a joint regulation.
  const setType = (code: string) => {
    const followsType = !value.issuer.trim() || value.issuer === regulationType(value.regulation_type)?.issuer
    onChange({ ...value, regulation_type: code, issuer: followsType ? regulationType(code)?.issuer ?? value.issuer : value.issuer })
  }
  const knownType = !!regulationType(value.regulation_type)

  return <>
    <fieldset className="form-section">
      <div className="form-grid">
        <label><FieldLabel text={t('admin.regulationType')} help="regulationType" />
          <select value={knownType ? regulationType(value.regulation_type)!.code : value.regulation_type} onChange={event => setType(event.target.value)}>
            {!knownType && <option value={value.regulation_type}>{value.regulation_type}</option>}
            {REGULATION_TYPES.map(type => <option key={type.code} value={type.code}>{t('admin.typeOption', { code: type.code, name: type.name })}</option>)}
          </select>
        </label>
        <label><FieldLabel text={t('admin.regulationNumber')} help="regulationNumber" />
          <input required maxLength={100} value={value.regulation_number} onChange={event => set('regulation_number', event.target.value)} placeholder={t('admin.regulationNumberPlaceholder')} />
        </label>
      </div>

      <label><FieldLabel text={t('admin.titleField')} help="title" />
        <textarea required rows={2} maxLength={1000} value={value.title} onChange={event => set('title', event.target.value)} placeholder={t('admin.titlePlaceholder')} />
      </label>

      <div className="form-grid">
        <label><FieldLabel text={t('admin.issuer')} help="issuer" />
          <input required maxLength={200} value={value.issuer} onChange={event => set('issuer', event.target.value)} />
        </label>
        <label><FieldLabel text={t('admin.topic')} help="topic" />
          <select value={value.topic} onChange={event => set('topic', event.target.value as MetadataValues['topic'])}>
            {(['PPh', 'PPN', 'other'] as const).map(topic => <option key={topic} value={topic}>{t(`admin.topics.${topic}`)}</option>)}
          </select>
        </label>
      </div>
    </fieldset>

    <fieldset className="form-section">
      <div className="form-grid three">
        <label><FieldLabel text={t('admin.issuedAt')} help="issuedAt" /><input type="date" value={value.issued_at ?? ''} onChange={event => setDate('issued_at', event.target.value)} /></label>
        <label><FieldLabel text={t('admin.effectiveFrom')} help="effectiveFrom" /><input type="date" value={value.effective_from ?? ''} onChange={event => setDate('effective_from', event.target.value)} /></label>
        <label><FieldLabel text={t('admin.effectiveUntil')} help="effectiveUntil" /><input type="date" value={value.effective_until ?? ''} min={value.effective_from ?? undefined} onChange={event => setDate('effective_until', event.target.value)} /></label>
      </div>
      <small className="form-note">{t('admin.datesHint')}</small>
    </fieldset>
  </>
}
