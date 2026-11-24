import { ChevronLeft, ChevronRight, FileText, LoaderCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { IngestionJob } from '../../../shared/types/tax'
import { regulationTypeName } from '../regulationTypes'

export const PAGE_SIZES = [10, 20, 50]

/** "PMK 28 TAHUN 2026" once the document is indexed; the file name or link before that. */
export function jobLabel(job: IngestionJob) {
  return job.regulation ? `${job.regulation.type} ${job.regulation.number}` : job.filename || job.source_url || ''
}

interface Props {
  jobs: IngestionJob[]
  page: number
  pageSize: number
  total: number
  filtered: boolean
  onPage: (page: number) => void
  onPageSize: (size: number) => void
  onClearFilters: () => void
  /** The table's own address (with page, filter, search), for the detail page's back link. */
  backTo: string
}

/** The document table. Each row links to its detail page; on phones the rows become cards (CSS). */
export function IngestionJobTable({ jobs, page, pageSize, total, filtered, onPage, onPageSize, onClearFilters, backTo }: Props) {
  const { t, i18n } = useTranslation()
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total ? (page - 1) * pageSize + 1 : 0
  const to = Math.min(total, page * pageSize)
  const updated = (value: string) => new Date(value).toLocaleString(i18n.resolvedLanguage, { dateStyle: 'medium', timeStyle: 'short' })

  if (!jobs.length) {
    return <div className="empty-panel compact">
      <p>{filtered ? t('admin.list.emptyFiltered') : t('admin.list.empty')}</p>
      {filtered && <button type="button" className="text-button" onClick={onClearFilters}>{t('admin.list.clearFilters')}</button>}
    </div>
  }

  return <>
    <div className="table-scroll">
      <table className="data-table jobs-table">
        <thead>
          <tr>
            <th scope="col">{t('admin.list.columns.regulation')}</th>
            <th scope="col">{t('admin.list.columns.topic')}</th>
            <th scope="col">{t('admin.list.columns.status')}</th>
            <th scope="col">{t('admin.list.columns.updated')}</th>
            <th scope="col"><span className="sr-only">{t('admin.list.columns.actions')}</span></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map(job => {
            const name = jobLabel(job)
            return <tr key={job.id}>
              <td data-label={t('admin.list.columns.regulation')}>
                <div className="job-cell">
                  <FileText size={16} aria-hidden="true" />
                  <div>
                    <Link className="job-name" to={`/admin/documents/${job.id}`} state={{ backTo }}>{name}</Link>
                    {job.regulation
                      ? <><span className="job-type">{regulationTypeName(job.regulation.type)}</span>
                        <span className="job-title">{job.regulation.title}</span></>
                      : <span className="job-type">{job.filename || t('admin.list.noFile')}</span>}
                    {job.error && <span className="job-error">{job.error}</span>}
                  </div>
                </div>
              </td>
              <td data-label={t('admin.list.columns.topic')}>{job.regulation ? (job.regulation.topic === 'other' ? t('admin.other') : job.regulation.topic) : '—'}</td>
              <td data-label={t('admin.list.columns.status')}>
                <span className={`job-status ${job.status}`}>
                  {(job.status === 'queued' || job.status === 'processing') && <LoaderCircle size={12} className="spin" aria-hidden="true" />}
                  {t(`admin.statuses.${job.status}`)}
                </span>
              </td>
              <td data-label={t('admin.list.columns.updated')}><time dateTime={job.updated_at}>{updated(job.updated_at)}</time></td>
              <td className="cell-action">
                <Link className="secondary-button small" to={`/admin/documents/${job.id}`} state={{ backTo }} aria-label={t('admin.list.openLabel', { name })}>
                  {t('admin.list.open')} <ChevronRight size={14} aria-hidden="true" />
                </Link>
              </td>
            </tr>
          })}
        </tbody>
      </table>
    </div>

    <nav className="pagination" aria-label={t('admin.list.pagination')}>
      <span className="pagination-summary">{t('admin.list.showing', { from, to, total })}</span>
      <label className="pagination-size">{t('admin.list.rowsPerPage')}
        <select value={pageSize} onChange={event => onPageSize(Number(event.target.value))}>
          {PAGE_SIZES.map(size => <option key={size} value={size}>{size}</option>)}
        </select>
      </label>
      <div className="pagination-pages">
        <button type="button" className="icon-btn" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label={t('admin.list.previous')}><ChevronLeft size={16} /></button>
        <span aria-current="page">{t('admin.list.page', { page })} / {pages}</span>
        <button type="button" className="icon-btn" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label={t('admin.list.next')}><ChevronRight size={16} /></button>
      </div>
    </nav>
  </>
}
