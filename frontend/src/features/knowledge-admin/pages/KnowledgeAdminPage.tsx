import { useCallback, useEffect, useMemo, useState } from 'react'
import { Check, LoaderCircle, Plus, Search, Settings, X } from 'lucide-react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { ApiRequest } from '../../../shared/api/client'
import { useAuth } from '../../../shared/auth/AuthProvider'
import type { IngestionJob } from '../../../shared/types/tax'
import { createIngestionApi } from '../api/ingestionApi'
import { IngestionJobTable, PAGE_SIZES } from '../components/IngestionJobTable'
import { useJobPage } from '../hooks/useIngestionJobs'

const STATUSES: IngestionJob['status'][] = ['review_required', 'approved', 'published', 'processing', 'queued', 'failed', 'rejected']
const SEARCH_DELAY_MS = 300

interface Props { request: ApiRequest }

/** Knowledge Admin home: the document table. Page, page size, status, and search live in the URL, so the
 * back button from a document returns to the same view. */
export function KnowledgeAdminPage({ request }: Props) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const api = useMemo(() => createIngestionApi(request), [request])
  const location = useLocation()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [error, setError] = useState('')
  const notice = (location.state as { notice?: string } | null)?.notice ?? ''

  const page = Math.max(1, Number(params.get('page')) || 1)
  const pageSize = PAGE_SIZES.includes(Number(params.get('size'))) ? Number(params.get('size')) : PAGE_SIZES[0]
  const status = (STATUSES as string[]).includes(params.get('status') ?? '') ? params.get('status') as IngestionJob['status'] : ''
  const search = params.get('q') ?? ''
  const [searchInput, setSearchInput] = useState(search)

  const update = useCallback((changes: Record<string, string | number | null>) => {
    setParams(current => {
      const next = new URLSearchParams(current)
      for (const [key, value] of Object.entries(changes)) {
        if (value === null || value === '' || (key === 'page' && value === 1)) next.delete(key)
        else next.set(key, String(value))
      }
      return next
    }, { replace: true })
  }, [setParams])

  // Search as the admin types, after a short pause; a new search starts at page 1.
  useEffect(() => {
    if (searchInput === search) return
    const timer = setTimeout(() => update({ q: searchInput.trim(), page: 1 }), SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [searchInput, search, update])

  const { data, loading, processing } = useJobPage(api, { page, pageSize, status, search }, setError)
  const counts = data?.status_counts ?? {}
  const allCount = Object.values(counts).reduce((sum, count) => sum + (count ?? 0), 0)

  // A page past the end (after deletions, or an old link) goes to the last page.
  useEffect(() => {
    if (data && data.total && page > Math.ceil(data.total / pageSize)) update({ page: Math.ceil(data.total / pageSize) })
  }, [data, page, pageSize, update])

  return <section className="page-panel wide admin-panel">
    <div className="page-kicker"><Settings size={16} /> {t('admin.eyebrow')}</div>
    <div className="page-title-row">
      <h1>{t('admin.title')}</h1>
      {isAdmin && <Link className="primary-button" to="/admin/documents/new"><Plus size={15} />{t('admin.list.add')}</Link>}
    </div>
    <p className="page-intro">{isAdmin ? t('admin.list.intro') : t('admin.reviewerIntro')}</p>

    {notice && <div className="success-banner" role="status"><Check size={15} />{notice}
      <button onClick={() => navigate(location.pathname + location.search, { replace: true, state: null })} aria-label={t('common.close')}><X size={14} /></button></div>}
    {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError('')} aria-label={t('common.close')}><X size={14} /></button></div>}

    <div className="table-toolbar">
      <label className="search-field">
        <Search size={15} aria-hidden="true" />
        <span className="sr-only">{t('admin.list.search')}</span>
        <input type="search" value={searchInput} onChange={event => setSearchInput(event.target.value)} placeholder={t('admin.list.searchPlaceholder')} />
      </label>
      <label className="status-filter">
        <span className="sr-only">{t('admin.list.status')}</span>
        <select value={status} onChange={event => update({ status: event.target.value, page: 1 })}>
          <option value="">{t('admin.list.allStatuses', { count: allCount })}</option>
          {STATUSES.map(value => <option key={value} value={value}>{t(`admin.statuses.${value}`)} ({counts[value] ?? 0})</option>)}
        </select>
      </label>
      {processing && <span className="jobs-live"><LoaderCircle size={13} className="spin" />{t('admin.autoRefresh')}</span>}
    </div>

    {loading && !data
      ? <div className="empty-panel compact"><p>{t('common.loading')}</p></div>
      : <IngestionJobTable
        jobs={data?.items ?? []} page={page} pageSize={pageSize} total={data?.total ?? 0}
        filtered={!!(status || search)}
        onPage={value => update({ page: value })}
        onPageSize={value => update({ size: value === PAGE_SIZES[0] ? null : value, page: 1 })}
        onClearFilters={() => { setSearchInput(''); update({ q: null, status: null, page: 1 }) }}
        backTo={location.pathname + location.search}
      />}
  </section>
}
