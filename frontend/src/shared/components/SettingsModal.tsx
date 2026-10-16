import type { FormEvent } from 'react'
import { Check, ShieldCheck, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface Props {
  open: boolean
  token: string
  onClose: () => void
  onSave: (token: string) => void
  onDisconnect: () => void
}

export function SettingsModal({ open, token, onClose, onSave, onDisconnect }: Props) {
  const { t } = useTranslation()
  if (!open) return null
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSave(new FormData(event.currentTarget).get('token')?.toString().trim() || '')
  }
  return <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div className="modal-heading"><div><span className="page-kicker"><ShieldCheck size={15} /> {t('settings.eyebrow')}</span><h2 id="settings-title">{t('settings.title')}</h2></div><button className="icon-btn" aria-label={t('settings.close')} onClick={onClose}><X size={18} /></button></div>
      <p>{t('settings.description')}</p>
      <form onSubmit={submit}><label>{t('settings.apiToken')}<input name="token" type="password" autoComplete="current-password" defaultValue={token} placeholder={t('settings.tokenPlaceholder')} required /></label><div className="modal-actions"><button className="text-button" type="button" onClick={onDisconnect}>{t('settings.disconnect')}</button><button className="primary-button" type="submit">{t('settings.save')} <Check size={15} /></button></div></form>
      <div className="token-note"><ShieldCheck size={15} /><span>{t('settings.privacy')}</span></div>
    </section>
  </div>
}
