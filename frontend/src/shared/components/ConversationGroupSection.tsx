import { useEffect, useRef, useState, type CSSProperties, type DragEvent, type FormEvent, type ReactNode } from 'react'
import { ChevronRight, Folder, FolderOpen, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import type { ConversationGroup } from '../types/tax'
import { ConfirmDialog } from './ConfirmDialog'
import { CONVERSATION_DRAG_TYPE, placeNear } from './ConversationItem'

type Mode = 'idle' | 'menu' | 'renaming' | 'confirmDelete'

interface Props {
  group: ConversationGroup
  count: number
  expanded: boolean
  children: ReactNode
  onToggle: () => void
  onRename: (name: string) => Promise<boolean>
  onDelete: () => Promise<boolean>
  onDropConversation: (conversationId: string) => void
}

/** A user's group in the sidebar: collapsible, renamable, deletable, and a drop target for conversations. */
export function ConversationGroupSection({ group, count, expanded, children, onToggle, onRename, onDelete, onDropConversation }: Props) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>('idle')
  const [name, setName] = useState(group.name)
  const [busy, setBusy] = useState(false)
  const [dropping, setDropping] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const more = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({})

  useEffect(() => {
    if (mode !== 'menu') return
    const close = (event: MouseEvent | KeyboardEvent) => {
      const inside = (node: Node) => root.current?.contains(node) || menu.current?.contains(node)
      if (event instanceof KeyboardEvent ? event.key === 'Escape' : !inside(event.target as Node)) setMode('idle')
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [mode])

  async function saveRename(event?: FormEvent) {
    event?.preventDefault()
    const next = name.trim()
    if (busy) return
    if (!next || next === group.name) { setMode('idle'); return }
    setBusy(true)
    const saved = await onRename(next.slice(0, 80))
    setBusy(false)
    if (saved) setMode('idle')
  }

  async function confirmDelete() {
    setBusy(true)
    const deleted = await onDelete()
    setBusy(false)
    if (!deleted) setMode('idle')
  }

  const accepts = (event: DragEvent) => event.dataTransfer.types.includes(CONVERSATION_DRAG_TYPE)
  const dropHandlers = {
    onDragOver: (event: DragEvent) => { if (accepts(event)) { event.preventDefault(); setDropping(true) } },
    onDragLeave: (event: DragEvent) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDropping(false) },
    onDrop: (event: DragEvent) => {
      setDropping(false)
      const id = event.dataTransfer.getData(CONVERSATION_DRAG_TYPE)
      if (id) { event.preventDefault(); onDropConversation(id) }
    },
  }

  return <div ref={root} className={`history-group ${dropping ? 'dropping' : ''}`} {...dropHandlers}>
    {mode === 'renaming'
      ? <form className="history-item editing history-group-header" onSubmit={saveRename}>
        <FolderOpen size={15} />
        <input
          autoFocus value={name} maxLength={80} disabled={busy} aria-label={t('groups.nameLabel')}
          onChange={event => setName(event.target.value)}
          onBlur={() => void saveRename()}
          onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); setMode('idle') } }}
        />
      </form>
      : <div className={`history-entry history-group-entry ${mode !== 'idle' ? 'active' : ''}`}>
        <button className="history-item history-group-header" aria-expanded={expanded} onClick={onToggle} title={group.name}>
          <ChevronRight size={13} className={`history-group-chevron ${expanded ? 'open' : ''}`} />
          {expanded ? <FolderOpen size={15} /> : <Folder size={15} />}
          <span>{group.name}</span>
          <small className="history-group-count">{count}</small>
        </button>
        <button ref={more} className="history-more" aria-label={t('groups.actions', { name: group.name })} aria-haspopup="menu"
          aria-expanded={mode === 'menu'}
          onClick={() => { if (mode === 'menu') { setMode('idle'); return } setMenuStyle(placeNear(more.current, 110)); setMode('menu') }}>
          <MoreHorizontal size={15} />
        </button>
      </div>}

    {expanded && <div className="history-group-items">
      {count ? children : <p className="history-group-empty">{t('groups.empty')}</p>}
    </div>}

    {mode === 'menu' && createPortal(<div ref={menu} className="history-menu" role="menu" style={menuStyle}>
      <button role="menuitem" onClick={() => { setName(group.name); setMode('renaming') }}><Pencil size={14} />{t('groups.rename')}</button>
      <button role="menuitem" className="danger" onClick={() => setMode('confirmDelete')}><Trash2 size={14} />{t('groups.delete')}</button>
    </div>, document.body)}

    {mode === 'confirmDelete' && <ConfirmDialog
      danger busy={busy}
      title={t('groups.confirmTitle')}
      message={t('groups.confirmText', { name: group.name, count })}
      confirmLabel={t('groups.delete')}
      cancelLabel={t('history.cancel')}
      onConfirm={() => void confirmDelete()}
      onCancel={() => setMode('idle')}
    />}
  </div>
}
