import { LoaderCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { IngestionJob } from '../../../shared/types/tax'

interface Props {
  jobs: IngestionJob[]
  loading: boolean
  processing: boolean
  selectedId: string | null
  onSelect: (id: string) => void
  onRefresh: () => void
}

export function jobLabel(job: IngestionJob) {
  return job.regulation ? `${job.regulation.type} ${job.regulation.number}` : job.filename || job.source_url
}

export function IngestionJobList({ jobs, loading, processing, selectedId, onSelect, onRefresh }: Props) {
  const { t, i18n } = useTranslation()
  const time = (value: string) => new Date(value).toLocaleString(i18n.resolvedLanguage, { dateStyle: 'medium', timeStyle: 'short' })

  return <>
    <div className="jobs-heading">
      <h2>{t('admin.recentJobs')}</h2>
      {processing && <span className="jobs-live"><LoaderCircle size={13} className="spin" />{t('admin.autoRefresh')}</span>}
      <button className="text-button" onClick={onRefresh}>{t('common.refresh')}</button>
    </div>
    {loading ? <div className="empty-panel compact"><p>{t('common.loading')}</p></div>
      : jobs.length ? <div className="jobs-list">{jobs.map(job =>
        <button type="button" key={job.id} className={`job-row ${selectedId === job.id ? 'selected' : ''}`} onClick={() => onSelect(job.id)} aria-pressed={selectedId === job.id}>
          <div>
            <strong>{jobLabel(job)}{job.regulation && <em> · {job.regulation.title}</em>}</strong>
            <span className={job.error ? 'job-error' : ''}>{job.error || job.detail || time(job.created_at)}</span>
          </div>
          <span className={`job-status ${job.status}`}>{t(`admin.statuses.${job.status}`)}</span>
        </button>)}
      </div>
      : <div className="empty-panel compact"><p>{t('admin.noJobs')}</p></div>}
  </>
}
