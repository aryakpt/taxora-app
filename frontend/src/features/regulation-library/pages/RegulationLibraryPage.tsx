import { useEffect, useState } from 'react'
import { BookOpen } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ApiRequest } from '../../../shared/api/client'
import type { Regulation } from '../../../shared/types/tax'
import { createRegulationsApi } from '../api/regulationsApi'
import { RegulationCard } from '../components/RegulationCard'

interface Props { request: ApiRequest; error: string; setError: (message: string) => void }

export function RegulationLibraryPage({ request, error, setError }: Props) {
  const { t } = useTranslation()
  const [regulations, setRegulations] = useState<Regulation[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    setError('')
    setLoading(true)
    createRegulationsApi(request).list().then(setRegulations).catch((cause: Error) => setError(cause.message)).finally(() => setLoading(false))
  }, [request, setError])
  return <section className="page-panel">
    <div className="page-kicker"><BookOpen size={16} /> {t('regulations.eyebrow')}</div><h1>{t('regulations.title')}</h1>
    <p className="page-intro">{t('regulations.intro')}</p>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {loading ? <div className="empty-panel" aria-live="polite">{t('common.loading')}</div> : regulations.length ? <div className="regulation-list">{regulations.map(regulation => <RegulationCard key={regulation.id} regulation={regulation} />)}</div> : <div className="empty-panel"><BookOpen size={24} /><h2>{t('regulations.emptyTitle')}</h2><p>{t('regulations.emptyDescription')}</p></div>}
  </section>
}
