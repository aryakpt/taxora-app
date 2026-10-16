import type { ApiRequest } from '../../../shared/api/client'
import type { IngestionJob } from '../../../shared/types/tax'

export interface IngestionSubmission {
  source_url: string
  regulation_number: string
  regulation_type: string
  title: string
  issuer: string
  topic: string
  issued_at: null
  effective_from: null
  effective_until: null
  is_internal: boolean
  allowed_user_ids: string[]
}

export function createIngestionApi(request: ApiRequest) {
  return {
    list: () => request<IngestionJob[]>('/api/v1/admin/ingestion'),
    submit: (body: IngestionSubmission) => request<IngestionJob>('/api/v1/admin/ingestion', { method: 'POST', data: body }),
  }
}
