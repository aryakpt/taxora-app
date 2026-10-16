import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
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
    (error: AxiosError<{ detail?: string }>) => {
      const message = error.response?.data?.detail || error.message || 'The API request failed.'
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
