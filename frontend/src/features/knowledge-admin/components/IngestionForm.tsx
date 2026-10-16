import { useState, type FormEvent } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export interface IngestionFormValues {
  source_url: string
  regulation_number: string
  regulation_type: string
  title: string
  issuer: string
  topic: string
}

interface Props { onSubmit: (values: IngestionFormValues) => Promise<void> }

export function IngestionForm({ onSubmit }: Props) {
  const { t } = useTranslation()
  const [form, setForm] = useState<IngestionFormValues>({ source_url: '', regulation_number: '', regulation_type: 'PMK', title: '', issuer: 'Ministry of Finance', topic: 'PPN' })
  async function submit(event: FormEvent) {
    event.preventDefault()
    await onSubmit(form)
  }

  return <form className="ingest-form" onSubmit={submit}>
    <h2>{t('admin.formTitle')}</h2><p>{t('admin.formDescription')}</p>
    <label>{t('admin.sourceUrl')}<input type="url" required value={form.source_url} onChange={event => setForm({ ...form, source_url: event.target.value })} placeholder="https://…" /></label>
    <div className="form-grid"><label>{t('admin.regulationNumber')}<input required value={form.regulation_number} onChange={event => setForm({ ...form, regulation_number: event.target.value })} placeholder={t('admin.regulationNumberPlaceholder')} /></label><label>{t('admin.regulationType')}<select value={form.regulation_type} onChange={event => setForm({ ...form, regulation_type: event.target.value })}>{['PMK', 'UU', 'PP', 'PER', 'Other'].map(type => <option key={type} value={type}>{type === 'Other' ? t('admin.other') : type}</option>)}</select></label></div>
    <label>{t('admin.titleField')}<input required value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} placeholder={t('admin.titlePlaceholder')} /></label>
    <div className="form-grid"><label>{t('admin.issuer')}<input required value={form.issuer} onChange={event => setForm({ ...form, issuer: event.target.value })} /></label><label>{t('admin.topic')}<select value={form.topic} onChange={event => setForm({ ...form, topic: event.target.value })}><option>PPN</option><option>PPh</option><option value="other">{t('admin.other')}</option></select></label></div>
    <button className="primary-button" type="submit">{t('admin.submit')} <ArrowUpRight size={15} /></button>
  </form>
}
