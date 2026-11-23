import { useEffect, useId, useRef } from 'react'
import { BookOpen, CircleHelp, MessageSquareText, ShieldAlert, X } from 'lucide-react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'

interface Props { onClose: () => void }

const ASK = ['ask1', 'ask2', 'ask3'] as const
const LABELS = [
  ['answered', 'answeredText'],
  ['general', 'generalText'],
  ['insufficient', 'insufficientText'],
  ['outOfScope', 'outOfScopeText'],
  ['failed', 'failedText'],
] as const
const LIMITS = ['limit1', 'limit2', 'limit3'] as const

/** What Taxora does, how to ask, and what the answer labels mean. Escape or the backdrop closes it. */
export function HelpDialog({ onClose }: Props) {
  const { t } = useTranslation()
  const titleId = useId()
  const close = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null
    close.current?.focus()
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); onClose() } }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); previouslyFocused?.focus?.() }
  }, [onClose])

  return createPortal(
    <div className="dialog-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
      <div className="help-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <header>
          <span className="help-dialog-icon" aria-hidden="true"><CircleHelp size={18} /></span>
          <h2 id={titleId}>{t('help.title')}</h2>
          <button ref={close} className="icon-btn" onClick={onClose} aria-label={t('common.close')}><X size={18} /></button>
        </header>
        <div className="help-dialog-body">
          <section>
            <h3><MessageSquareText size={15} />{t('help.askTitle')}</h3>
            <ul>{ASK.map(key => <li key={key}>{t(`help.${key}`)}</li>)}</ul>
          </section>
          <section>
            <h3><BookOpen size={15} />{t('help.labelsTitle')}</h3>
            <dl>{LABELS.map(([label, text]) => <div key={label}>
              <dt><span className={`help-label ${label}`}>{t(`help.${label}`)}</span></dt>
              <dd>{t(`help.${text}`)}</dd>
            </div>)}</dl>
          </section>
          <section>
            <h3><ShieldAlert size={15} />{t('help.limitsTitle')}</h3>
            <ul>{LIMITS.map(key => <li key={key}>{t(`help.${key}`)}</li>)}</ul>
          </section>
        </div>
      </div>
    </div>,
    document.body,
  )
}
