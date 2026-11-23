import { useRef, useState, type FormEvent } from 'react'
import { ArrowUpRight, FileUp, Link2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { RegulationMetadata } from '../api/ingestionApi'

type Mode = 'url' | 'upload'

const EMPTY: RegulationMetadata = {
  source_url: '', regulation_number: '', regulation_type: 'PMK', title: '', issuer: 'Kementerian Keuangan',
  topic: 'PPh', issued_at: null, effective_from: null, effective_until: null,
}
const REGULATION_TYPES = ['UU', 'PP', 'PMK', 'PER', 'SE', 'KEP']

interface Props { onSubmit: (metadata: RegulationMetadata, file: File | null) => Promise<boolean> }

export function IngestionForm({ onSubmit }: Props) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>('url')
  const [form, setForm] = useState<RegulationMetadata>(EMPTY)
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const set = <K extends keyof RegulationMetadata>(key: K, value: RegulationMetadata[K]) => setForm(current => ({ ...current, [key]: value }))
  const setDate = (key: 'issued_at' | 'effective_from' | 'effective_until', value: string) => set(key, value || null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      if (await onSubmit(form, mode === 'upload' ? file : null)) {
        setForm(EMPTY)
        setFile(null)
        if (fileInput.current) fileInput.current.value = ''
      }
    } finally { setBusy(false) }
  }

  return <form className="ingest-form" onSubmit={submit}>
    <h2>{t('admin.formTitle')}</h2>
    <p>{t('admin.formDescription')}</p>

    <div className="segmented" role="tablist" aria-label={t('admin.sourceMode')}>
      <button type="button" role="tab" aria-selected={mode === 'url'} className={mode === 'url' ? 'active' : ''} onClick={() => setMode('url')}><Link2 size={14} />{t('admin.modeUrl')}</button>
      <button type="button" role="tab" aria-selected={mode === 'upload'} className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}><FileUp size={14} />{t('admin.modeUpload')}</button>
    </div>

    {mode === 'upload' && <label>{t('admin.file')}
      <input ref={fileInput} type="file" accept="application/pdf,.pdf" required onChange={event => setFile(event.target.files?.[0] ?? null)} />
      <small>{t('admin.fileHint')}</small>
    </label>}

    <label>{t('admin.sourceUrl')}
      <input type="url" required value={form.source_url} onChange={event => set('source_url', event.target.value)} placeholder="https://peraturan.bpk.go.id/Download/…/….pdf" />
      <small>{mode === 'url' ? t('admin.sourceUrlHint') : t('admin.sourceUrlUploadHint')}</small>
    </label>

    <div className="form-grid">
      <label>{t('admin.regulationType')}
        <select value={form.regulation_type} onChange={event => set('regulation_type', event.target.value)}>
          {REGULATION_TYPES.map(type => <option key={type} value={type}>{type}</option>)}
        </select>
      </label>
      <label>{t('admin.regulationNumber')}
        <input required value={form.regulation_number} onChange={event => set('regulation_number', event.target.value)} placeholder={t('admin.regulationNumberPlaceholder')} />
      </label>
    </div>

    <label>{t('admin.titleField')}
      <input required value={form.title} onChange={event => set('title', event.target.value)} placeholder={t('admin.titlePlaceholder')} />
    </label>

    <div className="form-grid">
      <label>{t('admin.issuer')}
        <input required value={form.issuer} onChange={event => set('issuer', event.target.value)} />
      </label>
      <label>{t('admin.topic')}
        <select value={form.topic} onChange={event => set('topic', event.target.value as RegulationMetadata['topic'])}>
          <option value="PPh">PPh</option><option value="PPN">PPN</option><option value="other">{t('admin.other')}</option>
        </select>
      </label>
    </div>

    <div className="form-grid three">
      <label>{t('admin.issuedAt')}<input type="date" value={form.issued_at ?? ''} onChange={event => setDate('issued_at', event.target.value)} /></label>
      <label>{t('admin.effectiveFrom')}<input type="date" value={form.effective_from ?? ''} onChange={event => setDate('effective_from', event.target.value)} /></label>
      <label>{t('admin.effectiveUntil')}<input type="date" value={form.effective_until ?? ''} onChange={event => setDate('effective_until', event.target.value)} /></label>
    </div>
    <small className="form-note">{t('admin.datesHint')}</small>

    <button className="primary-button" type="submit" disabled={busy}>{busy ? t('admin.submitting') : t('admin.submit')} <ArrowUpRight size={15} /></button>
  </form>
}
