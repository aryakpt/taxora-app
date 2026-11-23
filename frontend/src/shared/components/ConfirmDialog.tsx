import { useEffect, useId, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import { createPortal } from 'react-dom'

interface Props {
  title: string
  message: string
  confirmLabel: string
  cancelLabel: string
  busy?: boolean
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/** A centred, modal confirmation. Cancel has focus first, so Enter never confirms by accident;
 * Escape or a click on the backdrop cancels; Tab stays inside the dialog. */
export function ConfirmDialog({ title, message, confirmLabel, cancelLabel, busy = false, danger = false, onConfirm, onCancel }: Props) {
  const titleId = useId()
  const messageId = useId()
  const dialog = useRef<HTMLDivElement>(null)
  const cancel = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null
    cancel.current?.focus()
    return () => previouslyFocused?.focus?.()
  }, [])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) { event.preventDefault(); onCancel() }
      if (event.key !== 'Tab' || !dialog.current) return
      const buttons = [...dialog.current.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')]
      if (!buttons.length) return
      const first = buttons[0], last = buttons[buttons.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [busy, onCancel])

  return createPortal(
    <div className="dialog-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onCancel() }}>
      <div ref={dialog} className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={messageId}>
        {danger && <div className="confirm-dialog-icon" aria-hidden="true"><AlertTriangle size={20} /></div>}
        <h2 id={titleId}>{title}</h2>
        <p id={messageId}>{message}</p>
        <div className="confirm-dialog-actions">
          <button ref={cancel} className="confirm-dialog-cancel" onClick={onCancel} disabled={busy}>{cancelLabel}</button>
          <button className={`confirm-dialog-confirm ${danger ? 'danger' : ''}`} onClick={onConfirm} disabled={busy}>{confirmLabel}</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
