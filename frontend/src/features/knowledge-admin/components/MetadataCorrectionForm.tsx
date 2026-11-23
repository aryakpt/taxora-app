import { useState, type FormEvent } from 'react'
import { History, PencilLine } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { IngestionJob } from '../../../shared/types/tax'
import type { MetadataCorrection } from '../api/ingestionApi'

interface Props {
  job: IngestionJob
  onSubmit: (correction: MetadataCorrection) => Promise<boolean>
}

const currentOf = (job: IngestionJob): MetadataCorrection => ({
  title: job.regulation?.title ?? '',
  issuer: job.regulation?.issuer ?? '',
  topic: (job.regulation?.topic ?? 'other') as MetadataCorrection['topic'],
  issued_at: job.version?.issued_at ?? null,
  effective_from: job.version?.effective_from ?? null,
  effective_until: job.version?.effective_until ?? null,
  reason: '',
})

/** Admin correction of an approved or published document. The legal text and the regulation number stay as reviewed. */
export function MetadataCorrectionForm({ job, onSubmit }: Props) {
  const { t, i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<MetadataCorrection>(() => currentOf(job))
  const [busy, setBusy] = useState(false)
  const set = <K extends keyof MetadataCorrection>(key: K, value: MetadataCorrection[K]) => setForm(current => ({ ...current, [key]: value }))
  const setDate = (key: 'issued_at' | 'effective_from' | 'effective_until', value: string) => set(key, value || null)
  const label = (field: string) => t(`admin.correction.fields.${field}`, { defaultValue: field })

  function start() {
    setForm(currentOf(job))
    setOpen(true)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try { if (await onSubmit(form)) setOpen(false) }
    finally { setBusy(false) }
  }

  return <section className="correction">
    <div className="correction-heading">
      <h3>{t('admin.correction.title')}</h3>
      {!open && <button className="secondary-button" onClick={start}><PencilLine size={14} />{t('admin.correction.open')}</button>}
    </div>
    <p className="muted">{t('admin.correction.intro')}</p>

    {open && <form className="correction-form" onSubmit={submit}>
      <label>{t('admin.titleField')}<input required value={form.title} onChange={event => set('title', event.target.value)} /></label>
      <div className="form-grid">
        <label>{t('admin.issuer')}<input required value={form.issuer} onChange={event => set('issuer', event.target.value)} /></label>
        <label>{t('admin.topic')}
          <select value={form.topic} onChange={event => set('topic', event.target.value as MetadataCorrection['topic'])}>
            <option value="PPh">PPh</option><option value="PPN">PPN</option><option value="other">{t('admin.other')}</option>
          </select>
        </label>
      </div>
      <div className="form-grid three">
        <label>{t('admin.issuedAt')}<input type="date" value={form.issued_at ?? ''} onChange={event => setDate('issued_at', event.target.value)} /></label>
        <label>{t('admin.effectiveFrom')}<input type="date" value={form.effective_from ?? ''} onChange={event => setDate('effective_from', event.target.value)} /></label>
        <label>{t('admin.effectiveUntil')}<input type="date" value={form.effective_until ?? ''} onChange={event => setDate('effective_until', event.target.value)} /></label>
      </div>
      <label>{t('admin.correction.reason')}
        <textarea required minLength={5} maxLength={500} rows={2} value={form.reason} onChange={event => set('reason', event.target.value)} placeholder={t('admin.correction.reasonPlaceholder')} />
      </label>
      {job.status === 'published' && <small>{t('admin.correction.liveNote')}</small>}
      <div className="correction-actions">
        <button className="primary-button" type="submit" disabled={busy || form.reason.trim().length < 5}>{t('admin.correction.save')}</button>
        <button className="text-button" type="button" onClick={() => setOpen(false)}>{t('admin.correction.cancel')}</button>
      </div>
    </form>}

    {job.corrections.length > 0 && <div className="correction-history">
      <h4><History size={13} />{t('admin.correction.history')}</h4>
      <ul>{job.corrections.map(entry => <li key={entry.at}>
        <div className="correction-meta">{new Date(entry.at).toLocaleString(i18n.resolvedLanguage)} · {entry.by ?? '-'}</div>
        <div className="correction-reason">“{entry.reason}”</div>
        <ul>{Object.entries(entry.changes).map(([field, change]) =>
          <li key={field}><strong>{label(field)}</strong>: {change.old ?? '—'} → {change.new ?? '—'}</li>)}</ul>
      </li>)}</ul>
    </div>}
  </section>
}
