import { useState } from 'react'
import { CircleHelp, Send, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface Props {
  busy: boolean
  error: string
  onSend: (question: string) => void
  onDismissError: () => void
}

export function ChatComposer({ busy, error, onSend, onDismissError }: Props) {
  const { t } = useTranslation()
  const [input, setInput] = useState('')
  function submit() {
    if (!input.trim() || busy) return
    onSend(input)
    setInput('')
  }
  return <div className="composer-wrap"><div className="composer-box">
    <textarea aria-label={t('composer.questionLabel')} value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }} placeholder={t('composer.questionPlaceholder')} rows={2} disabled={busy} />
    <div className="composer-bottom"><span className="composer-hint">{t('composer.keyboard')}</span><button className="send-button" onClick={submit} disabled={!input.trim() || busy} aria-label={t('composer.sendLabel')}>{busy ? <span className="send-spinner" /> : <Send size={15} />}<span>{t('composer.send')}</span></button></div>
  </div><p className="composer-disclaimer">{t('composer.disclaimer')}</p>{error && <div className="error-banner" role="alert"><CircleHelp size={15} />{error}<button aria-label={t('common.close')} onClick={onDismissError}><X size={14} /></button></div>}</div>
}
