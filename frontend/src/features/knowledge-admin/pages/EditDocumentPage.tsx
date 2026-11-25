import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { AlertTriangle, ArrowLeft, ExternalLink, FileText, Info, Settings, X } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ApiRequest } from '../../../shared/api/client'
import type { IngestionJob } from '../../../shared/types/tax'
import { createIngestionApi } from '../api/ingestionApi'
import { jobLabel } from '../components/IngestionJobTable'
import { MetadataFields, type MetadataValues } from '../components/MetadataFields'
import { isActive, useJob } from '../hooks/useIngestionJobs'

interface Props { request: ApiRequest }

const valuesOf = (job: IngestionJob): MetadataValues => ({
  regulation_type: job.regulation?.type ?? '',
  regulation_number: job.regulation?.number ?? '',
  title: job.regulation?.title ?? '',
  issuer: job.regulation?.issuer ?? '',
  topic: (job.regulation?.topic ?? 'other') as MetadataValues['topic'],
  issued_at: job.version?.issued_at ?? null,
  effective_from: job.version?.effective_from ?? null,
  effective_until: job.version?.effective_until ?? null,
})

const WARNED = ['published', 'approved', 'rejected', 'failed'] as const
// The server's rule (DocumentEdit.reason): trimmed, 5 to 500 characters.
const REASON_MIN = 5
const REASON_MAX = 500

/** Edit a document's metadata (admins). The file and its link stay; an approved, published, or rejected
 * document goes back to review (the server decides and records it). */
export function EditDocumentPage({ request }: Props) {
  const { t } = useTranslation()
  const { jobId = '' } = useParams()
  const api = useMemo(() => createIngestionApi(request), [request])
  const location = useLocation()
  const navigate = useNavigate()
  const listBackTo = (location.state as { backTo?: string } | null)?.backTo
  const detail = `/admin/documents/${jobId}`
  const [error, setError] = useState('')
  const showError = useCallback((message: string) => setError(message), [])
  const { job, missing } = useJob(api, jobId, showError)
  const [values, setValues] = useState<MetadataValues | null>(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (job && !values) setValues(valuesOf(job)) }, [job, values])

  const original = job ? JSON.stringify(valuesOf(job)) : ''
  const changed = !!values && JSON.stringify(values) !== original
  const warning = job && (WARNED as readonly string[]).includes(job.status) ? t(`admin.edit.warnings.${job.status}`) : ''
  const reasonLength = reason.trim().length
  const reasonOk = reasonLength >= REASON_MIN
  // Why "Save" is disabled, said next to it.
  const blocked = !changed ? t('admin.edit.needChange') : !reasonOk ? t('admin.edit.needReason', { min: REASON_MIN }) : ''

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!values || !job) return
    setBusy(true)
    try {
      const saved = await api.edit(job.id, { ...values, reason: reason.trim() })
      const backToReview = saved.status === 'review_required' && job.status !== 'review_required'
      navigate(detail, { state: { notice: t(backToReview ? 'admin.edit.savedReview' : 'admin.edit.saved'), backTo: listBackTo } })
    } catch (saveError) {
      setError((saveError as Error).message)
    } finally { setBusy(false) }
  }

  const back = <Link className="back-link" to={detail} state={{ backTo: listBackTo }}><ArrowLeft size={15} />{t('admin.edit.back')}</Link>

  if (missing) {
    return <section className="page-panel wide admin-panel">
      {back}
      <div className="empty-panel compact"><p>{t('admin.detail.notFound')}</p></div>
    </section>
  }

  return <section className="page-panel wide admin-panel">
    {back}
    <div className="page-kicker"><Settings size={16} /> {t('admin.eyebrow')}</div>
    <h1>{t('admin.edit.title')}{job && <span className="title-subject"> · {jobLabel(job)}</span>}</h1>
    {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label={t('common.close')}><X size={14} /></button></div>}

    {!job || !values
      ? <div className="empty-panel compact"><p>{t('common.loading')}</p></div>
      : isActive(job)
        ? <div className="empty-panel compact"><p>{t('admin.statuses.processing')}</p></div>
        : <form className="ingest-form" onSubmit={save}>
          <p className="form-intro">{t('admin.edit.intro')}</p>
          {warning && <p className="review-warning" role="note"><AlertTriangle size={14} />{warning}</p>}

          <fieldset className="form-section locked-source" disabled>
            <legend>{t('admin.edit.source')}</legend>
            <dl className="review-facts">
              {job.filename && <><dt><FileText size={13} /></dt><dd>{job.filename}</dd></>}
              <dt><ExternalLink size={13} /></dt>
              <dd>{job.source_url ? <a href={job.source_url} target="_blank" rel="noreferrer noopener">{job.source_url}</a> : t('admin.review.noSourceUrl')}</dd>
            </dl>
          </fieldset>

          <MetadataFields value={values} onChange={setValues} />

          <fieldset className="form-section">
            <label>
              <span className="field-label">{t('admin.edit.reason')}<span className="required-mark" aria-hidden="true">*</span></span>
              <textarea required minLength={REASON_MIN} maxLength={REASON_MAX} rows={2} value={reason} aria-describedby="edit-reason-hint"
                onChange={event => setReason(event.target.value)} placeholder={t('admin.edit.reasonPlaceholder')} />
              <small id="edit-reason-hint" className={`field-hint ${reasonOk ? 'met' : ''}`}>
                {t('admin.edit.reasonHint', { min: REASON_MIN })} · {reasonLength}/{REASON_MAX}
              </small>
            </label>
          </fieldset>

          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={busy || !!blocked} aria-describedby={blocked ? 'edit-blocked' : undefined}>
              {busy ? t('admin.edit.saving') : t('admin.edit.save')}
            </button>
            <Link className="text-button" to={detail} state={{ backTo: listBackTo }}>{t('admin.edit.cancel')}</Link>
            {blocked && <small id="edit-blocked" className="form-blocked" role="status"><Info size={13} aria-hidden="true" />{blocked}</small>}
          </div>
        </form>}
  </section>
}
