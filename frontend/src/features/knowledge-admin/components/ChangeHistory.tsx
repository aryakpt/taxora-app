import { History, RotateCcw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { DocumentChange } from '../../../shared/types/tax'

/** Every metadata change of a document, newest first: who, when, why, and each field's old and new value. */
export function ChangeHistory({ changes }: { changes: DocumentChange[] }) {
  const { t, i18n } = useTranslation()
  if (!changes.length) return null
  const field = (name: string) => t(`admin.edit.fields.${name}`, { defaultValue: name })

  return <section className="correction-history">
    <h3><History size={14} />{t('admin.edit.history')}</h3>
    <ul>{changes.map(entry => <li key={entry.at}>
      <div className="correction-meta">
        {new Date(entry.at).toLocaleString(i18n.resolvedLanguage)} · {entry.by ?? '-'}
        {entry.back_to_review && <span className="change-review"><RotateCcw size={12} />{t('admin.edit.backToReview')}</span>}
      </div>
      <div className="correction-reason">“{entry.reason}”</div>
      <ul>{Object.entries(entry.changes).map(([name, change]) =>
        <li key={name}><strong>{field(name)}</strong>: {change.old ?? '—'} → {change.new ?? '—'}</li>)}</ul>
    </li>)}</ul>
  </section>
}
