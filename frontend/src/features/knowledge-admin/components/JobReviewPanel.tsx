import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, Ban, CheckCircle2, Download, ExternalLink, RotateCcw, Send, Trash2, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ExtractedSection, IngestionJob } from '../../../shared/types/tax'
import type { IngestionApi, MetadataCorrection, VersionDates } from '../api/ingestionApi'
import { ConfirmDialog } from '../../../shared/components/ConfirmDialog'
import { jobLabel } from './IngestionJobList'
import { MetadataCorrectionForm } from './MetadataCorrectionForm'

interface Props {
  job: IngestionJob
  api: IngestionApi
  isAdmin: boolean
  onChanged: (job: IngestionJob, notice: string) => void
  onDeleted: (jobId: string, notice: string) => void
  onError: (message: string) => void
  onClose: () => void
}

const datesOf = (job: IngestionJob): VersionDates => ({
  issued_at: job.version?.issued_at ?? null,
  effective_from: job.version?.effective_from ?? null,
  effective_until: job.version?.effective_until ?? null,
})

export function JobReviewPanel({ job, api, isAdmin, onChanged, onDeleted, onError, onClose }: Props) {
  const { t, i18n } = useTranslation()
  const [sections, setSections] = useState<ExtractedSection[] | null>(null)
  const [dates, setDates] = useState<VersionDates>(() => datesOf(job))
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [dialog, setDialog] = useState<'reject' | 'delete' | null>(null)
  const [reason, setReason] = useState('')
  const panel = useRef<HTMLElement>(null)
  const underReview = job.status === 'review_required'
  const versionId = job.version?.id

  useEffect(() => { panel.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }, [])

  useEffect(() => {
    setSections(null)
    if (!versionId) return
    let current = true
    api.provisions(job.id).then(result => { if (current) setSections(result) }).catch((error: Error) => onError(error.message))
    return () => { current = false }
  }, [api, job.id, versionId, onError])

  // Follow the server whenever this job changes (another reviewer, or our own save).
  const serverDates = JSON.stringify(datesOf(job))
  useEffect(() => { setDates(JSON.parse(serverDates)); setConfirmed(false) }, [job.id, serverDates])

  async function run(action: () => Promise<IngestionJob>, notice: string) {
    setBusy(true)
    try { onChanged(await action(), notice) }
    catch (error) { onError((error as Error).message) }
    finally { setBusy(false) }
  }

  async function correct(correction: MetadataCorrection) {
    try {
      onChanged(await api.correctMetadata(job.id, correction), t('admin.correction.saved'))
      return true
    } catch (error) {
      onError((error as Error).message)
      return false
    }
  }

  async function reject() {
    setBusy(true)
    try {
      onChanged(await api.reject(job.id, reason.trim()), t('admin.review.rejected'))
      setDialog(null)
      setReason('')
    } catch (error) { onError((error as Error).message) }
    finally { setBusy(false) }
  }

  async function remove() {
    setBusy(true)
    try {
      await api.remove(job.id)
      onDeleted(job.id, t('admin.review.deleted', { name: jobLabel(job) }))
    } catch (error) {
      onError((error as Error).message)
      setDialog(null)
    } finally { setBusy(false) }
  }

  const processing = job.status === 'queued' || job.status === 'processing'
  const correctable = isAdmin && !!job.version && (job.status === 'approved' || job.status === 'published')
  const sectionLabel = (section: ExtractedSection) => {
    if (section.kind === 'article') return t('admin.review.article', { number: section.number })
    if (section.kind === 'elucidation' && section.number) return t('admin.review.elucidationOf', { number: section.number })
    return t(`admin.review.kinds.${section.kind}`)
  }
  const datesChanged = JSON.stringify(dates) !== serverDates
  const setDate = (key: keyof VersionDates, value: string) => setDates(current => ({ ...current, [key]: value || null }))

  return <section ref={panel} className="review-panel" aria-label={t('admin.review.title')}>
    <header className="review-header">
      <div>
        <span className={`job-status ${job.status}`}>{t(`admin.statuses.${job.status}`)}</span>
        <h2>{jobLabel(job)}</h2>
        {job.regulation && <p>{job.regulation.title}</p>}
      </div>
      <button className="icon-btn" onClick={onClose} aria-label={t('common.close')}><X size={17} /></button>
    </header>

    <dl className="review-facts">
      {job.regulation && <><dt>{t('admin.issuer')}</dt><dd>{job.regulation.issuer}</dd><dt>{t('admin.topic')}</dt><dd>{job.regulation.topic === 'other' ? t('admin.other') : job.regulation.topic}</dd></>}
      <dt>{t('admin.sourceUrl')}</dt>
      <dd>{job.source_url
        ? <a href={job.source_url} target="_blank" rel="noreferrer noopener">{job.source_url} <ExternalLink size={12} /></a>
        : <span className="muted">{t('admin.review.noSourceUrl')}</span>}</dd>
      {job.rejection && <><dt>{t('admin.review.rejectedBecause')}</dt><dd className="job-error">“{job.rejection.reason}” · {job.rejection.by ?? '-'}</dd></>}
      {job.detail && <><dt>{t('admin.review.result')}</dt><dd>{job.detail}</dd></>}
      {job.error && <><dt>{t('admin.review.error')}</dt><dd className="job-error">{job.error}</dd></>}
      {job.version?.verified_at && <><dt>{t('admin.review.verifiedAt')}</dt><dd>{new Date(job.version.verified_at).toLocaleString(i18n.resolvedLanguage)}</dd></>}
    </dl>

    {job.storage_available && <button className="secondary-button" onClick={() => void api.downloadOriginal(job).catch((error: Error) => onError(error.message))}>
      <Download size={14} />{t('admin.review.downloadOriginal')}
    </button>}

    {job.version && <fieldset className="review-dates" disabled={!underReview || busy}>
      <legend>{t('admin.review.dates')}</legend>
      <div className="form-grid three">
        <label>{t('admin.issuedAt')}<input type="date" value={dates.issued_at ?? ''} onChange={event => setDate('issued_at', event.target.value)} /></label>
        <label>{t('admin.effectiveFrom')}<input type="date" value={dates.effective_from ?? ''} onChange={event => setDate('effective_from', event.target.value)} /></label>
        <label>{t('admin.effectiveUntil')}<input type="date" value={dates.effective_until ?? ''} onChange={event => setDate('effective_until', event.target.value)} /></label>
      </div>
      {underReview
        ? <button className="secondary-button" disabled={!datesChanged} onClick={() => void run(() => api.updateDates(job.id, dates), t('admin.review.datesSaved'))}>{t('admin.review.saveDates')}</button>
        : job.status !== 'rejected' && <small>{t('admin.review.datesFrozen')}</small>}
    </fieldset>}

    {correctable && <MetadataCorrectionForm key={job.updated_at} job={job} onSubmit={correct} />}

    {job.version && <div className="review-sections">
      <h3>{t('admin.review.sections')}{sections && <span> · {t('admin.review.sectionCount', { count: sections.length })}</span>}</h3>
      {sections === null ? <p className="muted">{t('common.loading')}</p> : sections.map(section =>
        <details key={section.id}>
          <summary>
            <strong>{sectionLabel(section)}</strong>
            <span>{t('admin.review.sectionMeta', { chars: section.text.length.toLocaleString(i18n.resolvedLanguage), chunks: section.chunks })}</span>
          </summary>
          <pre>{section.text}</pre>
        </details>)}
    </div>}

    <footer className="review-actions">
      {underReview && <>
        {!job.version?.effective_from && <p className="review-warning"><AlertTriangle size={14} />{t('admin.review.noEffectiveDate')}</p>}
        <label className="checkbox"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />{t('admin.review.confirm')}</label>
        <button className="primary-button" disabled={!confirmed || datesChanged || busy} onClick={() => void run(() => api.approve(job.id), t('admin.review.approved'))}>
          <CheckCircle2 size={15} />{t('admin.review.approve')}
        </button>
        {datesChanged && <small>{t('admin.review.saveFirst')}</small>}
        <button className="secondary-button danger" disabled={busy} onClick={() => setDialog('reject')}><Ban size={14} />{t('admin.review.reject')}</button>
      </>}
      {job.status === 'approved' && (isAdmin
        ? <button className="primary-button" disabled={busy} onClick={() => void run(() => api.publish(job.id), t('admin.review.published'))}><Send size={15} />{t('admin.review.publish')}</button>
        : <p className="muted">{t('admin.review.waitingForAdmin')}</p>)}
      {job.status === 'failed' && isAdmin && <button className="primary-button" disabled={busy} onClick={() => void run(() => api.retry(job.id), t('admin.review.retried'))}><RotateCcw size={15} />{t('admin.review.retry')}</button>}
      {job.status === 'published' && <p className="muted">{t('admin.review.isPublished')}</p>}
      {job.status === 'rejected' && <p className="muted">{t('admin.review.isRejected')}</p>}
      {isAdmin && !processing && <button className="text-button danger review-delete" disabled={busy} onClick={() => setDialog('delete')}>
        <Trash2 size={14} />{t('admin.review.delete')}
      </button>}
    </footer>

    {dialog === 'reject' && <ConfirmDialog
      danger busy={busy} confirmDisabled={reason.trim().length < 5}
      title={t('admin.review.rejectTitle')}
      message={t('admin.review.rejectText', { name: jobLabel(job) })}
      confirmLabel={t('admin.review.reject')} cancelLabel={t('history.cancel')}
      onConfirm={() => void reject()} onCancel={() => setDialog(null)}
    >
      <label className="dialog-field">{t('admin.review.rejectReason')}
        <textarea rows={3} maxLength={500} value={reason} onChange={event => setReason(event.target.value)} placeholder={t('admin.review.rejectPlaceholder')} />
      </label>
    </ConfirmDialog>}

    {dialog === 'delete' && <ConfirmDialog
      danger busy={busy}
      title={t('admin.review.deleteTitle')}
      message={t(job.status === 'published' ? 'admin.review.deletePublishedText' : 'admin.review.deleteText', { name: jobLabel(job) })}
      confirmLabel={t('admin.review.delete')} cancelLabel={t('history.cancel')}
      onConfirm={() => void remove()} onCancel={() => setDialog(null)}
    />}
  </section>
}
