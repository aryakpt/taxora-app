import { useCallback, useMemo, useState } from 'react'
import { Check, Settings, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ApiRequest } from '../../../shared/api/client'
import { useAuth } from '../../../shared/auth/AuthProvider'
import type { IngestionJob } from '../../../shared/types/tax'
import { createIngestionApi, type RegulationMetadata } from '../api/ingestionApi'
import { IngestionForm } from '../components/IngestionForm'
import { IngestionJobList } from '../components/IngestionJobList'
import { JobReviewPanel } from '../components/JobReviewPanel'
import { useIngestionJobs } from '../hooks/useIngestionJobs'

interface Props { request: ApiRequest }

export function KnowledgeAdminPage({ request }: Props) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const api = useMemo(() => createIngestionApi(request), [request])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const showError = useCallback((message: string) => { setNotice(''); setError(message) }, [])
  const { jobs, loading, processing, refresh, replace, removeJob } = useIngestionJobs(api, showError)
  const selected = jobs.find(job => job.id === selectedId) ?? null

  function changed(job: IngestionJob, message: string) {
    replace(job)
    setError('')
    setNotice(message)
  }

  function deleted(jobId: string, message: string) {
    removeJob(jobId)
    setSelectedId(null)
    setError('')
    setNotice(message)
    void refresh()  // duplicate jobs of the same document were deleted too
  }

  async function submit(metadata: RegulationMetadata, file: File | null) {
    try {
      const job = file ? await api.upload(metadata, file) : await api.submitUrl(metadata)
      changed(job, t('admin.submitted'))
      setSelectedId(job.id)
      return true
    } catch (submissionError) {
      showError((submissionError as Error).message)
      return false
    }
  }

  return <section className="page-panel admin-panel">
    <div className="page-kicker"><Settings size={16} /> {t('admin.eyebrow')}</div>
    <h1>{t('admin.title')}</h1>
    <p className="page-intro">{isAdmin ? t('admin.intro') : t('admin.reviewerIntro')}</p>
    {notice && <div className="success-banner" role="status"><Check size={15} />{notice}</div>}
    {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label={t('common.close')}><X size={14} /></button></div>}
    {isAdmin && <IngestionForm onSubmit={submit} />}
    <IngestionJobList jobs={jobs} loading={loading} processing={processing} selectedId={selectedId} onSelect={setSelectedId} onRefresh={() => void refresh()} />
    {selected && <JobReviewPanel key={selected.id} job={selected} api={api} isAdmin={isAdmin} onChanged={changed} onDeleted={deleted} onError={showError} onClose={() => setSelectedId(null)} />}
  </section>
}
