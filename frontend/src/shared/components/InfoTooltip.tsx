import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { CircleHelp } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface Props {
  /** What the tooltip explains, for the button's accessible name ("Explain: Issuing authority"). */
  label: string
  children: string
}

/** A small "?" next to a field label. Opens on hover, on keyboard focus, and on tap (touch screens have no
 * hover); Escape, leaving it, or a tap elsewhere closes it. The text is linked with aria-describedby, so screen readers
 * read it with the button. */
export function InfoTooltip({ label, children }: Props) {
  const { t } = useTranslation()
  const id = useId()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLSpanElement>(null)
  const bubble = useRef<HTMLSpanElement>(null)
  const [shift, setShift] = useState(0)

  // Keep the bubble on screen: near the right edge (or on a narrow phone) it moves left as far as needed.
  useLayoutEffect(() => {
    const element = bubble.current
    if (!open || !element) { setShift(0); return }
    const margin = 8
    element.style.transform = ''
    const rect = element.getBoundingClientRect()
    // clientWidth, not innerWidth: on phones an overflowing bubble widens the layout viewport (innerWidth).
    const overflowRight = rect.right - (document.documentElement.clientWidth - margin)
    const overflowLeft = margin - rect.left
    setShift(overflowRight > 0 ? -Math.min(overflowRight, rect.left - margin) : overflowLeft > 0 ? overflowLeft : 0)
  }, [open])

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent | KeyboardEvent | TouchEvent) => {
      if (event instanceof KeyboardEvent ? event.key === 'Escape' : !root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('keydown', close)
    document.addEventListener('mousedown', close)
    document.addEventListener('touchstart', close)
    return () => {
      document.removeEventListener('keydown', close)
      document.removeEventListener('mousedown', close)
      document.removeEventListener('touchstart', close)
    }
  }, [open])

  return <span ref={root} className="info-tooltip" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button
      type="button"
      className="info-tooltip-button"
      aria-label={t('common.explain', { label })}
      aria-describedby={id}
      aria-expanded={open}
      onClick={event => { event.preventDefault(); setOpen(true) }}  // a tap also focuses: toggling would close it at once
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <CircleHelp size={14} aria-hidden="true" />
    </button>
    <span ref={bubble} id={id} role="tooltip" className="info-tooltip-text" hidden={!open}
      style={shift ? { transform: `translateX(${shift}px)` } : undefined}>{children}</span>
  </span>
}
