import { useCallback, useEffect, useState } from 'react'
import type { IngestionJob } from '../../../shared/types/tax'
import type { IngestionApi, JobPage, JobQuery } from '../api/ingestionApi'

const POLL_INTERVAL_MS = 3_000
export const isActive = (job: IngestionJob) => job.status === 'queued' || job.status === 'processing'

/** One page of the job table; refreshes itself while a job on the page is still being processed. */
export function useJobPage(api: IngestionApi, query: JobQuery, onError: (message: string) => void) {
  const [data, setData] = useState<JobPage | null>(null)
  const [loading, setLoading] = useState(true)
  const { page, pageSize, status, search } = query

  const refresh = useCallback(async () => {
    try { setData(await api.list({ page, pageSize, status, search })) }
    catch (error) { onError((error as Error).message) }
    finally { setLoading(false) }
  }, [api, page, pageSize, status, search, onError])

  useEffect(() => { setLoading(true); void refresh() }, [refresh])

  const processing = data?.items.some(isActive) ?? false
  useEffect(() => {
    if (!processing) return
    const timer = setInterval(() => void refresh(), POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [processing, refresh])

  return { data, loading, processing, refresh }
}

/** One job for its detail page; refreshes itself while it is being processed. */
export function useJob(api: IngestionApi, id: string, onError: (message: string) => void) {
  const [job, setJob] = useState<IngestionJob | null>(null)
  const [missing, setMissing] = useState(false)

  const refresh = useCallback(async () => {
    try { setJob(await api.get(id)); setMissing(false) }
    catch (error) {
      if ([404, 422].includes((error as { status?: number }).status ?? 0)) setMissing(true)  // 422: not a job id
      else onError((error as Error).message)
    }
  }, [api, id, onError])

  useEffect(() => { setJob(null); void refresh() }, [refresh])

  const processing = job ? isActive(job) : false
  useEffect(() => {
    if (!processing) return
    const timer = setInterval(() => void refresh(), POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [processing, refresh])

  return { job, setJob, missing, refresh }
}
