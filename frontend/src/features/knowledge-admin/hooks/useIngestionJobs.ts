import { useCallback, useEffect, useState } from 'react'
import type { IngestionJob } from '../../../shared/types/tax'
import type { IngestionApi } from '../api/ingestionApi'

const POLL_INTERVAL_MS = 3_000
const isActive = (job: IngestionJob) => job.status === 'queued' || job.status === 'processing'

/** Job list that refreshes itself while any job is still being processed in the background. */
export function useIngestionJobs(api: IngestionApi, onError: (message: string) => void) {
  const [jobs, setJobs] = useState<IngestionJob[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try { setJobs(await api.list()) }
    catch (error) { onError((error as Error).message) }
    finally { setLoading(false) }
  }, [api, onError])

  useEffect(() => { void refresh() }, [refresh])

  const processing = jobs.some(isActive)
  useEffect(() => {
    if (!processing) return
    const timer = setInterval(() => void refresh(), POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [processing, refresh])

  /** Replace one job with the server's answer after an action, without waiting for a full refresh. */
  const replace = useCallback((job: IngestionJob) => {
    setJobs(current => current.some(item => item.id === job.id)
      ? current.map(item => item.id === job.id ? job : item)
      : [job, ...current])
  }, [])

  return { jobs, loading, processing, refresh, replace }
}
