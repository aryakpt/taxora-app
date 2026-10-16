import type { IngestionJob } from '../../../shared/types/tax'
import { useTranslation } from 'react-i18next'

interface Props { jobs: IngestionJob[]; onRefresh: () => void }

export function IngestionJobList({ jobs, onRefresh }: Props) {
  const { t } = useTranslation()
  return <>
    <div className="jobs-heading"><h2>{t('admin.recentJobs')}</h2><button className="text-button" onClick={onRefresh}>{t('common.refresh')}</button></div>
    {jobs.length ? <div className="jobs-list">{jobs.map(job => <div className="job-row" key={job.id}><div><strong>{job.source_url}</strong><span>{job.error || job.created_at || t('admin.noDetails')}</span></div><span className={`job-status ${job.status}`}>{t(`admin.statuses.${job.status}`, { defaultValue: job.status.replace(/_/g, ' ') })}</span></div>)}</div> : <div className="empty-panel compact"><p>{t('admin.noJobs')}</p></div>}
  </>
}
