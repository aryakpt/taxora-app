import { useCallback, useMemo, useState } from 'react'
import { ArrowLeft, Check, Settings, X } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ApiRequest } from '../../../shared/api/client'
import { useAuth } from '../../../shared/auth/AuthProvider'
import type { IngestionJob } from '../../../shared/types/tax'
import { createIngestionApi } from '../api/ingestionApi'
import { JobReviewPanel } from '../components/JobReviewPanel'
import { useJob } from '../hooks/useIngestionJobs'

interface Props { request: ApiRequest }

/** One document: its facts, extracted sections, and the review actions. */
export function DocumentDetailPage({ request }: Props) {
  const { t } = useTranslation()
  const { jobId = '' } = useParams()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const api = useMemo(() => createIngestionApi(request), [request])
  const location = useLocation()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const state = location.state as { notice?: string, backTo?: string } | null
  const [notice, setNotice] = useState(state?.notice ?? '')
  // Back to the table as it was left (page, filter, search) when we came from it.
  const backTo = state?.backTo?.startsWith('/admin') ? state.backTo : '/admin'
  const showError = useCallback((message: string) => { setNotice(''); setError(message) }, [])
  const { job, setJob, missing } = useJob(api, jobId, showError)

  function changed(updated: IngestionJob, message: string) {
    setJob(updated)
    setError('')
    setNotice(message)
  }

  function deleted(_: string, message: string) {
    navigate(backTo, { state: { notice: message } })
  }

  return <section className="page-panel wide admin-panel">
    <Link className="back-link" to={backTo}><ArrowLeft size={15} />{t('admin.detail.back')}</Link>
    <div className="page-kicker"><Settings size={16} /> {t('admin.eyebrow')}</div>
    {notice && <div className="success-banner" role="status"><Check size={15} />{notice}<button onClick={() => setNotice('')} aria-label={t('common.close')}><X size={14} /></button></div>}
    {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label={t('common.close')}><X size={14} /></button></div>}
    {missing
      ? <div className="empty-panel compact"><p>{t('admin.detail.notFound')}</p><Link className="text-button" to={backTo}>{t('admin.detail.back')}</Link></div>
      : job
        ? <JobReviewPanel key={job.id} job={job} api={api} isAdmin={isAdmin} onChanged={changed} onDeleted={deleted} onError={showError} />
        : <div className="empty-panel compact"><p>{t('common.loading')}</p></div>}
  </section>
}
