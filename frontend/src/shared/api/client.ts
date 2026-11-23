import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'

// Production calls the API on its own origin: Vercel forwards /api/* to the backend (vercel.json), so the
// session cookie is first-party. Development talks to the local API directly.
const API_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

/** FastAPI sends a string for handled errors and a list of field errors for validation (422). */
function describeDetail(detail: string | { msg?: string }[] | undefined): string | undefined {
  if (Array.isArray(detail)) return detail.map(item => item.msg?.replace(/^Value error, /, '')).filter(Boolean).join('; ')
  return detail
}

function createHttpClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_URL,
    timeout: 30_000,
    withCredentials: true,
    headers: { Accept: 'application/json' },
  })

  client.interceptors.response.use(
    response => response,
    (error: AxiosError<{ detail?: string | { msg?: string }[] }>) => {
      const message = describeDetail(error.response?.data?.detail) || error.message || 'The API request failed.'
      return Promise.reject(new ApiError(message, error.response?.status))
    },
  )

  return client
}

export function createApiClient() {
  const http = createHttpClient()

  return async function request<T>(path: string, config: AxiosRequestConfig = {}): Promise<T> {
    const response = await http.request<T>({ url: path, ...config })
    return response.data
  }
}

export type ApiRequest = ReturnType<typeof createApiClient>
