import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react'
import { Check, Folder, FolderMinus, History, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import type { ConversationGroup, ConversationSummary } from '../types/tax'
import { ConfirmDialog } from './ConfirmDialog'

type Mode = 'idle' | 'menu' | 'renaming' | 'confirmDelete'

// The history list scrolls (and the mobile sidebar is transformed), so a menu inside it would be cut off or
// misplaced. Menus are rendered into <body> and placed against the viewport, below the button, or above it
// when there is not enough room below.
export function placeNear(button: HTMLElement | null, room: number): CSSProperties {
  if (!button) return {}
  const rect = button.getBoundingClientRect()
  const right = window.innerWidth - rect.right
  return window.innerHeight - rect.bottom < room
    ? { position: 'fixed', right, bottom: window.innerHeight - rect.top + 2 }
    : { position: 'fixed', right, top: rect.bottom + 2 }
}

interface Props {
  item: ConversationSummary
  selected: boolean
  onOpen: () => void
  groups: ConversationGroup[]
  onRename: (title: string) => Promise<boolean>
  onMove: (groupId: string | null) => Promise<boolean>
  onDelete: () => Promise<boolean>
}

/** Drag data type for moving a conversation onto a group in the sidebar. */
export const CONVERSATION_DRAG_TYPE = 'application/x-taxora-conversation'

/** One conversation in the sidebar history, with a menu to rename it, move it to a group, or delete it (after a
 * confirmation dialog). It can also be dragged onto a group. */
export function ConversationItem({ item, selected, groups, onOpen, onRename, onMove, onDelete }: Props) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>('idle')
  const [title, setTitle] = useState(item.title)
  const [busy, setBusy] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const more = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({})
  // Rename and delete, plus the move section: a label, one row per group, and "remove from group".
  const menuRoom = 110 + (groups.length ? 30 + groups.length * 34 : 0) + (item.group_id ? 34 : 0)

  useEffect(() => {
    if (mode !== 'menu') return
    const close = (event: MouseEvent | KeyboardEvent) => {
      const inside = (node: Node) => root.current?.contains(node) || menu.current?.contains(node)
      if (event instanceof KeyboardEvent ? event.key === 'Escape' : !inside(event.target as Node)) setMode('idle')
    }
    // The menu is fixed to the viewport, so it follows its row when the history list scrolls or the
    // window resizes. (Closing on scroll instead made it vanish when a late scroll event arrived.)
    const list = root.current?.closest('.history-list')
    const follow = () => setMenuStyle(placeNear(more.current, menuRoom))
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
  }, [mode, menuRoom])

  function show(next: Mode) {
    setMenuStyle(placeNear(more.current, menuRoom))
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

  async function moveTo(groupId: string | null) {
    setMode('idle')
    if (groupId !== (item.group_id ?? null)) await onMove(groupId)
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
    <button className={`history-item ${selected ? 'selected' : ''}`} onClick={onOpen} title={item.title} draggable
      onDragStart={event => { event.dataTransfer.setData(CONVERSATION_DRAG_TYPE, item.id); event.dataTransfer.effectAllowed = 'move' }}>
      <History size={15} /><span>{item.title}</span>
    </button>
    <button ref={more} className="history-more" aria-label={t('history.actions', { title: item.title })} aria-haspopup="menu"
      aria-expanded={mode === 'menu'} onClick={() => (mode === 'menu' ? setMode('idle') : show('menu'))}>
      <MoreHorizontal size={15} />
    </button>

    {mode === 'menu' && createPortal(<div ref={menu} className="history-menu" role="menu" style={menuStyle}>
      <button role="menuitem" onClick={startRename}><Pencil size={14} />{t('history.rename')}</button>
      {groups.length > 0 && <>
        <div className="history-menu-label" role="presentation">{t('groups.moveTo')}</div>
        {groups.map(group => <button key={group.id} role="menuitemradio" aria-checked={item.group_id === group.id}
          onClick={() => void moveTo(group.id)}>
          <Folder size={14} /><span className="history-menu-text">{group.name}</span>
          {item.group_id === group.id && <Check size={14} className="history-menu-check" />}
        </button>)}
        {item.group_id && <button role="menuitem" onClick={() => void moveTo(null)}><FolderMinus size={14} />{t('groups.removeFromGroup')}</button>}
        <div className="history-menu-divider" role="presentation" />
      </>}
      <button role="menuitem" className="danger" onClick={() => setMode('confirmDelete')}><Trash2 size={14} />{t('history.delete')}</button>
    </div>, document.body)}

    {mode === 'confirmDelete' && <ConfirmDialog
      danger busy={busy}
      title={t('history.confirmTitle')}
      message={t('history.confirmText', { title: item.title })}
      confirmLabel={t('history.delete')}
      cancelLabel={t('history.cancel')}
      onConfirm={() => void confirmDelete()}
      onCancel={() => setMode('idle')}
    />}
  </div>
}
