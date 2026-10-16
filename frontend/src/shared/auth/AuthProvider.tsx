import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { createApiClient } from '../api/client'

export interface AuthUser {
  id: string
  email: string | null
  full_name: string | null
  role: string
}

interface Credentials { email: string; password: string }
interface Registration extends Credentials { full_name: string }

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  signIn: (credentials: Credentials) => Promise<void>
  signUp: (details: Registration) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const request = useMemo(() => createApiClient(), [])
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    request<AuthUser>('/api/v1/auth/me')
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [request])

  const signIn = useCallback(async (credentials: Credentials) => {
    const account = await request<AuthUser>('/api/v1/auth/login', { method: 'POST', data: credentials })
    setUser(account)
  }, [request])

  const signUp = useCallback(async (details: Registration) => {
    const account = await request<AuthUser>('/api/v1/auth/register', { method: 'POST', data: details })
    setUser(account)
  }, [request])

  const signOut = useCallback(async () => {
    try { await request<void>('/api/v1/auth/logout', { method: 'POST' }) }
    finally { setUser(null) }
  }, [request])

  const value = useMemo(() => ({ user, loading, signIn, signUp, signOut }), [user, loading, signIn, signUp, signOut])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
