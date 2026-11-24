import { useRef, useState, type FormEvent } from 'react'
import { ArrowUpRight, FileUp, Link2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { RegulationMetadata } from '../api/ingestionApi'
import { REGULATION_TYPES, regulationType } from '../regulationTypes'
import { FieldLabel } from './FieldLabel'

type Mode = 'url' | 'upload'

const DEFAULT_TYPE = 'PMK'
const EMPTY: RegulationMetadata = {
  source_url: '', regulation_number: '', regulation_type: DEFAULT_TYPE, title: '',
  issuer: regulationType(DEFAULT_TYPE)!.issuer, topic: 'PPh', issued_at: null, effective_from: null, effective_until: null,
}

interface Props { onSubmit: (metadata: RegulationMetadata, file: File | null) => Promise<boolean> }

export function IngestionForm({ onSubmit }: Props) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>('url')
  const [form, setForm] = useState<RegulationMetadata>(EMPTY)
  // The issuer follows the regulation type until the admin edits it (e.g. a joint regulation).
  const [issuerEdited, setIssuerEdited] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const set = <K extends keyof RegulationMetadata>(key: K, value: RegulationMetadata[K]) => setForm(current => ({ ...current, [key]: value }))
  const setDate = (key: 'issued_at' | 'effective_from' | 'effective_until', value: string) => set(key, value || null)
  const setType = (code: string) => setForm(current => ({
    ...current, regulation_type: code, issuer: issuerEdited ? current.issuer : regulationType(code)?.issuer ?? current.issuer,
  }))

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      if (await onSubmit(form, mode === 'upload' ? file : null)) {
        setForm(EMPTY)
        setIssuerEdited(false)
        setFile(null)
        if (fileInput.current) fileInput.current.value = ''
      }
    } finally { setBusy(false) }
  }

  return <form className="ingest-form" onSubmit={submit}>
    <p className="form-intro">{t('admin.formDescription')}</p>

    <fieldset className="form-section">
      <legend><FieldLabel text={t('admin.sourceMode')} help="sourceMode" /></legend>
      <div className="segmented" role="tablist" aria-label={t('admin.sourceMode')}>
        <button type="button" role="tab" aria-selected={mode === 'url'} className={mode === 'url' ? 'active' : ''} onClick={() => setMode('url')}><Link2 size={14} />{t('admin.modeUrl')}</button>
        <button type="button" role="tab" aria-selected={mode === 'upload'} className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}><FileUp size={14} />{t('admin.modeUpload')}</button>
      </div>

      {mode === 'upload' && <label><FieldLabel text={t('admin.file')} help="file" />
        <input ref={fileInput} type="file" accept="application/pdf,.pdf" required onChange={event => setFile(event.target.files?.[0] ?? null)} />
        <small>{file ? t('admin.fileChosen', { name: file.name }) : t('admin.fileHint')}</small>
      </label>}

      <label><FieldLabel text={mode === 'url' ? t('admin.sourceUrl') : t('admin.sourceUrlOptional')} help="sourceUrl" />
        <input type="url" required={mode === 'url'} value={form.source_url} onChange={event => set('source_url', event.target.value)} placeholder="https://peraturan.bpk.go.id/Download/…/….pdf" />
        <small>{mode === 'url' ? t('admin.sourceUrlHint') : t('admin.sourceUrlUploadHint')}</small>
      </label>
    </fieldset>

    <fieldset className="form-section">
      <div className="form-grid">
        <label><FieldLabel text={t('admin.regulationType')} help="regulationType" />
          <select value={form.regulation_type} onChange={event => setType(event.target.value)}>
            {REGULATION_TYPES.map(type => <option key={type.code} value={type.code}>{t('admin.typeOption', { code: type.code, name: type.name })}</option>)}
          </select>
        </label>
        <label><FieldLabel text={t('admin.regulationNumber')} help="regulationNumber" />
          <input required value={form.regulation_number} onChange={event => set('regulation_number', event.target.value)} placeholder={t('admin.regulationNumberPlaceholder')} />
        </label>
      </div>

      <label><FieldLabel text={t('admin.titleField')} help="title" />
        <textarea required rows={2} maxLength={1000} value={form.title} onChange={event => set('title', event.target.value)} placeholder={t('admin.titlePlaceholder')} />
      </label>

      <div className="form-grid">
        <label><FieldLabel text={t('admin.issuer')} help="issuer" />
          <input required maxLength={200} value={form.issuer} onChange={event => { setIssuerEdited(true); set('issuer', event.target.value) }} />
        </label>
        <label><FieldLabel text={t('admin.topic')} help="topic" />
          <select value={form.topic} onChange={event => set('topic', event.target.value as RegulationMetadata['topic'])}>
            {(['PPh', 'PPN', 'other'] as const).map(topic => <option key={topic} value={topic}>{t(`admin.topics.${topic}`)}</option>)}
          </select>
        </label>
      </div>
    </fieldset>

    <fieldset className="form-section">
      <div className="form-grid three">
        <label><FieldLabel text={t('admin.issuedAt')} help="issuedAt" /><input type="date" value={form.issued_at ?? ''} onChange={event => setDate('issued_at', event.target.value)} /></label>
        <label><FieldLabel text={t('admin.effectiveFrom')} help="effectiveFrom" /><input type="date" value={form.effective_from ?? ''} onChange={event => setDate('effective_from', event.target.value)} /></label>
        <label><FieldLabel text={t('admin.effectiveUntil')} help="effectiveUntil" /><input type="date" value={form.effective_until ?? ''} onChange={event => setDate('effective_until', event.target.value)} /></label>
      </div>
      <small className="form-note">{t('admin.datesHint')}</small>
    </fieldset>

    <button className="primary-button" type="submit" disabled={busy}>{busy ? t('admin.submitting') : t('admin.submit')} <ArrowUpRight size={15} /></button>
  </form>
}
