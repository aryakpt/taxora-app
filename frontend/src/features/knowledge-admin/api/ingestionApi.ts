import type { ApiRequest } from '../../../shared/api/client'
import type { ExtractedSection, IngestionJob } from '../../../shared/types/tax'

const BASE = '/api/v1/admin/ingestion'
const UPLOAD_TIMEOUT_MS = 120_000

/** Metadata the admin supplies for a document. Dates are ISO strings (yyyy-mm-dd) or null. */
export interface RegulationMetadata {
  source_url: string
  regulation_number: string
  regulation_type: string
  title: string
  issuer: string
  topic: 'PPh' | 'PPN' | 'other'
  issued_at: string | null
  effective_from: string | null
  effective_until: string | null
}

export interface VersionDates {
  issued_at: string | null
  effective_from: string | null
  effective_until: string | null
}

export interface MetadataCorrection extends VersionDates {
  title: string
  issuer: string
  topic: RegulationMetadata['topic']
  reason: string
}

export function createIngestionApi(request: ApiRequest) {
  const action = (id: string, name: 'approve' | 'publish' | 'retry') =>
    request<IngestionJob>(`${BASE}/${id}/${name}`, { method: 'POST' })

  return {
    list: () => request<IngestionJob[]>(BASE),
    submitUrl: (metadata: RegulationMetadata) => request<IngestionJob>(BASE, { method: 'POST', data: metadata }),
    upload: (metadata: RegulationMetadata, file: File) => {
      const form = new FormData()
      for (const [key, value] of Object.entries(metadata)) if (value !== null) form.append(key, value)
      form.append('file', file)
      return request<IngestionJob>(`${BASE}/upload`, { method: 'POST', data: form, timeout: UPLOAD_TIMEOUT_MS })
    },
    provisions: (id: string) => request<ExtractedSection[]>(`${BASE}/${id}/provisions`),
    updateDates: (id: string, dates: VersionDates) => request<IngestionJob>(`${BASE}/${id}/dates`, { method: 'PUT', data: dates }),
    correctMetadata: (id: string, correction: MetadataCorrection) =>
      request<IngestionJob>(`${BASE}/${id}/metadata`, { method: 'PUT', data: correction }),
    approve: (id: string) => action(id, 'approve'),
    publish: (id: string) => action(id, 'publish'),
    retry: (id: string) => action(id, 'retry'),
    /** Fetches the stored PDF with the session cookie and hands it to the browser as a download. */
    downloadOriginal: async (job: IngestionJob) => {
      const blob = await request<Blob>(`${BASE}/${job.id}/document`, { responseType: 'blob', timeout: UPLOAD_TIMEOUT_MS })
      const url = URL.createObjectURL(blob)
      const link = Object.assign(document.createElement('a'), { href: url, download: job.filename || 'dokumen.pdf' })
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1_000)
    },
  }
}

export type IngestionApi = ReturnType<typeof createIngestionApi>
