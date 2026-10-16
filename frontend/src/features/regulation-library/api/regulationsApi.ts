import type { ApiRequest } from '../../../shared/api/client'
import type { Regulation } from '../../../shared/types/tax'

export function createRegulationsApi(request: ApiRequest) {
  return { list: () => request<Regulation[]>('/api/v1/regulations') }
}
