import { useEffect, useState } from 'react'
import { Check, Settings } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ApiRequest } from '../../../shared/api/client'
import type { IngestionJob } from '../../../shared/types/tax'
import { createIngestionApi } from '../api/ingestionApi'
import { IngestionForm, type IngestionFormValues } from '../components/IngestionForm'
import { IngestionJobList } from '../components/IngestionJobList'

interface Props { request: ApiRequest; error: string; setError: (error: string) => void }

export function KnowledgeAdminPage({ request, error, setError }: Props) {
  const { t } = useTranslation()
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [notice, setNotice] = useState('')
  useEffect(() => {
    setError('')
    createIngestionApi(request).list().then(setJobs).catch((cause: Error) => setError(cause.message))
  }, [request, setError])
  async function submit(values: IngestionFormValues) {
    try {
      await createIngestionApi(request).submit({ ...values, issued_at: null, effective_from: null, effective_until: null, is_internal: false, allowed_user_ids: [] })
      setNotice(t('admin.submitted'))
      setJobs(await createIngestionApi(request).list())
    } catch (submissionError) { setError((submissionError as Error).message) }
  }
  async function refreshJobs() {
    try { setJobs(await createIngestionApi(request).list()) }
    catch (refreshError) { setError((refreshError as Error).message) }
  }

  return <section className="page-panel admin-panel">
    <div className="page-kicker"><Settings size={16} /> {t('admin.eyebrow')}</div><h1>{t('admin.title')}</h1>
    <p className="page-intro">{t('admin.intro')}</p>
    {notice && <div className="success-banner"><Check size={15} />{notice}</div>}{error && <div className="error-banner" role="alert">{error}</div>}
    <IngestionForm onSubmit={submit} />
    <IngestionJobList jobs={jobs} onRefresh={refreshJobs} />
  </section>
}
