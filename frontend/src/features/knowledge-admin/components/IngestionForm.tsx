import { useRef, useState, type FormEvent } from 'react'
import { ArrowUpRight, FileUp, Link2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { RegulationMetadata } from '../api/ingestionApi'
import { regulationType } from '../regulationTypes'
import { FieldLabel } from './FieldLabel'
import { MetadataFields } from './MetadataFields'

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
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const set = <K extends keyof RegulationMetadata>(key: K, value: RegulationMetadata[K]) => setForm(current => ({ ...current, [key]: value }))

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

    <MetadataFields value={form} onChange={metadata => setForm(current => ({ ...current, ...metadata }))} />

    <button className="primary-button" type="submit" disabled={busy}>{busy ? t('admin.submitting') : t('admin.submit')} <ArrowUpRight size={15} /></button>
  </form>
}
