import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createApiClient } from '../../api/client'

// Google Identity Services: https://developers.google.com/identity/gsi/web
const GIS_SCRIPT = 'https://accounts.google.com/gsi/client'

interface GoogleAccounts {
  accounts: {
    id: {
      initialize: (options: { client_id: string; callback: (response: { credential: string }) => void; ux_mode?: 'popup' }) => void
      renderButton: (parent: HTMLElement, options: Record<string, string | number>) => void
    }
  }
}

declare global {
  interface Window { google?: GoogleAccounts }
}

let scriptLoading: Promise<void> | null = null

function loadScript(): Promise<void> {
  if (window.google?.accounts) return Promise.resolve()
  scriptLoading ??= new Promise((resolve, reject) => {
    const script = Object.assign(document.createElement('script'), { src: GIS_SCRIPT, async: true, defer: true })
    script.onload = () => resolve()
    script.onerror = () => { scriptLoading = null; reject(new Error('Google sign-in could not be loaded')) }
    document.head.appendChild(script)
  })
  return scriptLoading
}

interface Props {
  onCredential: (credential: string) => void
}

/** Google's own button (and an "or" divider) when the backend has a Google client ID configured; nothing otherwise. */
export function GoogleSignInButton({ onCredential }: Props) {
  const { t, i18n } = useTranslation()
  const container = useRef<HTMLDivElement>(null)
  const [clientId, setClientId] = useState<string | null>(null)
  const callback = useRef(onCredential)
  callback.current = onCredential

  useEffect(() => {
    createApiClient()<{ google_client_id: string | null }>('/api/v1/auth/providers')
      .then(providers => setClientId(providers.google_client_id))
      .catch(() => setClientId(null))
  }, [])

  useEffect(() => {
    if (!clientId || !container.current) return
    let active = true
    loadScript().then(() => {
      if (!active || !container.current || !window.google) return
      window.google.accounts.id.initialize({ client_id: clientId, ux_mode: 'popup', callback: response => callback.current(response.credential) })
      container.current.replaceChildren()
      window.google.accounts.id.renderButton(container.current, {
        type: 'standard', theme: 'outline', size: 'large', shape: 'rectangular', text: 'continue_with',
        width: Math.min(container.current.offsetWidth || 360, 400), locale: i18n.resolvedLanguage === 'id' ? 'id' : 'en',
      })
    }).catch(() => { /* The email form still works without Google. */ })
    return () => { active = false }
  }, [clientId, i18n.resolvedLanguage])

  if (!clientId) return null
  return <>
    <div className="google-sign-in" ref={container} />
    <div className="auth-divider"><span>{t('auth.orWithEmail')}</span></div>
  </>
}

