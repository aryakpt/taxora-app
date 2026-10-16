import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

function createHttpClient(getToken: () => string): AxiosInstance {
  const client = axios.create({
    baseURL: API_URL,
    timeout: 30_000,
    headers: { Accept: 'application/json' },
  })

  client.interceptors.request.use(config => {
    const token = getToken()
    if (token) config.headers.set('Authorization', `Bearer ${token}`)
    else config.headers.delete('Authorization')
    return config
  })

  client.interceptors.response.use(
    response => response,
    (error: AxiosError<{ detail?: string }>) => {
      const message = error.response?.data?.detail || error.message || 'The API request failed.'
      return Promise.reject(new ApiError(message, error.response?.status))
    },
  )

  return client
}

export function createApiClient(getToken: () => string) {
  const http = createHttpClient(getToken)

  return async function request<T>(path: string, config: AxiosRequestConfig = {}): Promise<T> {
    const response = await http.request<T>({ url: path, ...config })
    return response.data
  }
}

export type ApiRequest = ReturnType<typeof createApiClient>
