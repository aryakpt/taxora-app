import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react'
import { History, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import type { ConversationSummary } from '../types/tax'

type Mode = 'idle' | 'menu' | 'renaming' | 'confirmDelete'

// The history list scrolls (and the mobile sidebar is transformed), so a menu inside it would be cut off or
// misplaced. Menus are rendered into <body> and placed against the viewport, below the button, or above it
// when there is not enough room below.
const MENU_ROOM = 150

function placeNear(button: HTMLElement | null): CSSProperties {
  if (!button) return {}
  const rect = button.getBoundingClientRect()
  const right = window.innerWidth - rect.right
  return window.innerHeight - rect.bottom < MENU_ROOM
    ? { position: 'fixed', right, bottom: window.innerHeight - rect.top + 2 }
    : { position: 'fixed', right, top: rect.bottom + 2 }
}

interface Props {
  item: ConversationSummary
  selected: boolean
  onOpen: () => void
  onRename: (title: string) => Promise<boolean>
  onDelete: () => Promise<boolean>
}

/** One conversation in the sidebar history, with a menu to rename it or delete it (after confirmation). */
export function ConversationItem({ item, selected, onOpen, onRename, onDelete }: Props) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>('idle')
  const [title, setTitle] = useState(item.title)
  const [busy, setBusy] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const more = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({})

  useEffect(() => {
    if (mode !== 'menu' && mode !== 'confirmDelete') return
    const close = (event: MouseEvent | KeyboardEvent) => {
      const inside = (node: Node) => root.current?.contains(node) || menu.current?.contains(node)
      if (event instanceof KeyboardEvent ? event.key === 'Escape' : !inside(event.target as Node)) setMode('idle')
    }
    // The menu is fixed to the viewport, so it follows its row when the history list scrolls or the
    // window resizes. (Closing on scroll instead made it vanish when a late scroll event arrived.)
    const list = root.current?.closest('.history-list')
    const follow = () => setMenuStyle(placeNear(more.current))
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    list?.addEventListener('scroll', follow)
    window.addEventListener('resize', follow)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
      list?.removeEventListener('scroll', follow)
      window.removeEventListener('resize', follow)
    }
  }, [mode])

  function show(next: Mode) {
    setMenuStyle(placeNear(more.current))
    setMode(next)
  }

  function startRename() {
    setTitle(item.title)
    setMode('renaming')
  }

  async function saveRename(event?: FormEvent) {
    event?.preventDefault()
    const next = title.trim()
    if (busy) return
    if (!next || next === item.title) { setMode('idle'); return }
    setBusy(true)
    const saved = await onRename(next.slice(0, 120))
    setBusy(false)
    if (saved) setMode('idle')
  }

  async function confirmDelete() {
    setBusy(true)
    const deleted = await onDelete()
    setBusy(false)
    if (!deleted) setMode('idle')
  }

  if (mode === 'renaming') {
    return <form className="history-item editing" onSubmit={saveRename}>
      <History size={15} />
      <input
        autoFocus value={title} maxLength={120} disabled={busy} aria-label={t('history.renameLabel')}
        onChange={event => setTitle(event.target.value)}
        onBlur={() => void saveRename()}
        onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); setMode('idle') } }}
      />
    </form>
  }

  return <div ref={root} className={`history-entry ${selected ? 'selected' : ''} ${mode !== 'idle' ? 'active' : ''}`}>
    <button className={`history-item ${selected ? 'selected' : ''}`} onClick={onOpen} title={item.title}>
      <History size={15} /><span>{item.title}</span>
    </button>
    <button ref={more} className="history-more" aria-label={t('history.actions', { title: item.title })} aria-haspopup="menu"
      aria-expanded={mode === 'menu'} onClick={() => (mode === 'menu' ? setMode('idle') : show('menu'))}>
      <MoreHorizontal size={15} />
    </button>

    {mode === 'menu' && createPortal(<div ref={menu} className="history-menu" role="menu" style={menuStyle}>
      <button role="menuitem" onClick={startRename}><Pencil size={14} />{t('history.rename')}</button>
      <button role="menuitem" className="danger" onClick={() => show('confirmDelete')}><Trash2 size={14} />{t('history.delete')}</button>
    </div>, document.body)}

    {mode === 'confirmDelete' && createPortal(<div ref={menu} className="history-menu confirm" role="alertdialog" aria-label={t('history.confirmTitle')} style={menuStyle}>
      <p>{t('history.confirmText')}</p>
      <div className="history-confirm-actions">
        <button className="danger solid" onClick={() => void confirmDelete()} disabled={busy}>{t('history.delete')}</button>
        <button onClick={() => setMode('idle')} disabled={busy}>{t('history.cancel')}</button>
      </div>
    </div>, document.body)}
  </div>
}
