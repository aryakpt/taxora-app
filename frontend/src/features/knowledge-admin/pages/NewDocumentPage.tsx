import { useMemo, useState } from 'react'
import { ArrowLeft, Settings, X } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ApiRequest } from '../../../shared/api/client'
import { createIngestionApi, type RegulationMetadata } from '../api/ingestionApi'
import { IngestionForm } from '../components/IngestionForm'

interface Props { request: ApiRequest }

/** Add a regulation (admins only). After submitting, the new document's page shows its processing. */
export function NewDocumentPage({ request }: Props) {
  const { t } = useTranslation()
  const api = useMemo(() => createIngestionApi(request), [request])
  const navigate = useNavigate()
  const [error, setError] = useState('')

  async function submit(metadata: RegulationMetadata, file: File | null) {
    try {
      const job = file ? await api.upload(metadata, file) : await api.submitUrl(metadata)
      navigate(`/admin/documents/${job.id}`, { state: { notice: t('admin.submitted') } })
      return true
    } catch (submissionError) {
      setError((submissionError as Error).message)
      return false
    }
  }

  return <section className="page-panel wide admin-panel">
    <Link className="back-link" to="/admin"><ArrowLeft size={15} />{t('admin.newDocument.back')}</Link>
    <div className="page-kicker"><Settings size={16} /> {t('admin.eyebrow')}</div>
    <h1>{t('admin.newDocument.title')}</h1>
    {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label={t('common.close')}><X size={14} /></button></div>}
    <IngestionForm onSubmit={submit} />
  </section>
}
