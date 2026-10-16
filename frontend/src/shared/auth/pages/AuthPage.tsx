import { useState, type FormEvent } from 'react'
import { ArrowRight, ShieldCheck, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../AuthProvider'
import { LanguageSwitcher } from '../../components/LanguageSwitcher'
import { ApiError } from '../../api/client'

type Mode = 'login' | 'register'

export function AuthPage() {
  const { t } = useTranslation()
  const { signIn, signUp } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (mode === 'register' && password !== confirmation) {
      setError(t('auth.passwordsDoNotMatch'))
      return
    }
    setBusy(true)
    try {
      if (mode === 'login') await signIn({ email, password })
      else await signUp({ email, password, full_name: fullName })
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) setError(t('auth.invalidCredentials'))
      else if (cause instanceof ApiError && cause.status === 409) setError(t('auth.emailAlreadyRegistered'))
      else setError(t('auth.requestFailed'))
    }
    finally { setBusy(false) }
  }

  function toggleMode() {
    setMode(mode === 'login' ? 'register' : 'login')
    setError('')
  }

  return <main className="auth-screen">
    <div className="auth-toolbar"><a className="brand auth-brand" href="/"><span className="brand-mark"><span /></span><span className="brand-name">taxora</span></a><LanguageSwitcher /></div>
    <section className="auth-card" aria-labelledby="auth-title">
      <div className="auth-emblem"><Sparkles size={20} /></div>
      <p className="auth-eyebrow"><ShieldCheck size={13} /> {t('auth.secureAccount')}</p>
      <h1 id="auth-title">{t(mode === 'login' ? 'auth.loginTitle' : 'auth.registerTitle')}</h1>
      <p className="auth-description">{t(mode === 'login' ? 'auth.loginDescription' : 'auth.registerDescription')}</p>

      <form className="auth-form" onSubmit={submit}>
        {mode === 'register' && <label>{t('auth.fullName')}<input autoComplete="name" value={fullName} onChange={event => setFullName(event.target.value)} required maxLength={150} /></label>}
        <label>{t('auth.email')}<input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required maxLength={320} /></label>
        <label>{t('auth.password')}<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} required minLength={mode === 'register' ? 12 : 1} maxLength={128} />{mode === 'register' && <small>{t('auth.passwordRequirement')}</small>}</label>
        {mode === 'register' && <label>{t('auth.confirmPassword')}<input type="password" autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} required minLength={12} maxLength={128} /></label>}
        {error && <div className="error-banner" role="alert">{error}</div>}
        <button className="auth-submit" type="submit" disabled={busy}>{busy ? t('auth.working') : t(mode === 'login' ? 'auth.signIn' : 'auth.createAccount')}<ArrowRight size={16} /></button>
      </form>

      <p className="auth-switch">{t(mode === 'login' ? 'auth.noAccount' : 'auth.hasAccount')} <button type="button" onClick={toggleMode}>{t(mode === 'login' ? 'auth.createAccount' : 'auth.signIn')}</button></p>
      <p className="auth-privacy"><ShieldCheck size={14} /> {t('auth.providerKeyNotice')}</p>
    </section>
    <p className="auth-footer">{t('auth.footer')}</p>
  </main>
}
