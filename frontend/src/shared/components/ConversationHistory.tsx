import { useState, type DragEvent, type FormEvent } from 'react'
import { FolderPlus, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ConversationGroup, ConversationSummary } from '../types/tax'
import { ConversationGroupSection } from './ConversationGroupSection'
import { CONVERSATION_DRAG_TYPE, ConversationItem } from './ConversationItem'

const COLLAPSED_KEY = 'taxora-collapsed-groups'

function savedCollapsed(): string[] {
  try { return JSON.parse(localStorage.getItem(COLLAPSED_KEY) || '[]') } catch { return [] }
}

export interface HistoryActions {
  onOpenConversation: (id: string) => void
  onRenameConversation: (id: string, title: string) => Promise<boolean>
  onMoveConversation: (id: string, groupId: string | null) => Promise<boolean>
  onDeleteConversation: (id: string) => Promise<boolean>
  onCreateGroup: (name: string) => Promise<boolean>
  onRenameGroup: (id: string, name: string) => Promise<boolean>
  onDeleteGroup: (id: string) => Promise<boolean>
}

interface Props extends HistoryActions {
  activeConversation: string | null
  conversations: ConversationSummary[]
  groups: ConversationGroup[]
}

/** The sidebar history: the user's groups (collapsible) first, then conversations not in a group. */
export function ConversationHistory({ activeConversation, conversations, groups, ...actions }: Props) {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState<string[]>(savedCollapsed)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)
  const [droppingOut, setDroppingOut] = useState(false)

  function toggle(id: string) {
    const next = collapsed.includes(id) ? collapsed.filter(item => item !== id) : [...collapsed, id]
    setCollapsed(next)
    try { localStorage.setItem(COLLAPSED_KEY, JSON.stringify(next)) } catch { /* remembered for this visit only */ }
  }

  async function create(event?: FormEvent) {
    event?.preventDefault()
    const name = newName.trim()
    if (busy) return
    if (!name) { setCreating(false); return }
    setBusy(true)
    const created = await actions.onCreateGroup(name.slice(0, 80))
    setBusy(false)
    if (created) { setCreating(false); setNewName('') }
  }

  const item = (conversation: ConversationSummary) => <ConversationItem
    key={conversation.id} item={conversation} groups={groups} selected={activeConversation === conversation.id}
    onOpen={() => actions.onOpenConversation(conversation.id)}
    onRename={title => actions.onRenameConversation(conversation.id, title)}
    onMove={groupId => actions.onMoveConversation(conversation.id, groupId)}
    onDelete={() => actions.onDeleteConversation(conversation.id)}
  />

  const known = new Set(groups.map(group => group.id))
  const ungrouped = conversations.filter(conversation => !conversation.group_id || !known.has(conversation.group_id))
  // Dropping a grouped conversation on the ungrouped list takes it out of its group.
  const dropOut = {
    onDragOver: (event: DragEvent) => {
      if (groups.length && event.dataTransfer.types.includes(CONVERSATION_DRAG_TYPE)) { event.preventDefault(); setDroppingOut(true) }
    },
    onDragLeave: (event: DragEvent) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDroppingOut(false) },
    onDrop: (event: DragEvent) => {
      setDroppingOut(false)
      const id = event.dataTransfer.getData(CONVERSATION_DRAG_TYPE)
      const dragged = conversations.find(conversation => conversation.id === id)
      if (dragged?.group_id) { event.preventDefault(); void actions.onMoveConversation(id, null) }
    },
  }

  return <>
    <div className="history-heading">
      <span>{t('navigation.recent')}</span>
      <div className="history-heading-actions">
        <button aria-label={t('groups.new')} title={t('groups.new')} className="icon-btn" onClick={() => setCreating(true)}><FolderPlus size={15} /></button>
        <button aria-label={t('navigation.searchConversations')} title={t('navigation.searchConversations')} className="icon-btn"><Search size={15} /></button>
      </div>
    </div>
    <div className="history-list">
      {creating && <form className="history-item editing" onSubmit={create}>
        <FolderPlus size={15} />
        <input autoFocus value={newName} maxLength={80} disabled={busy} placeholder={t('groups.namePlaceholder')}
          aria-label={t('groups.nameLabel')} onChange={event => setNewName(event.target.value)} onBlur={() => void create()}
          onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); setCreating(false); setNewName('') } }} />
      </form>}

      {groups.map(group => {
        const members = conversations.filter(conversation => conversation.group_id === group.id)
        return <ConversationGroupSection
          key={group.id} group={group} count={members.length} expanded={!collapsed.includes(group.id)}
          onToggle={() => toggle(group.id)}
          onRename={name => actions.onRenameGroup(group.id, name)}
          onDelete={() => actions.onDeleteGroup(group.id)}
          onDropConversation={id => void actions.onMoveConversation(id, group.id)}
        >{members.map(item)}</ConversationGroupSection>
      })}

      <div className={`history-ungrouped ${droppingOut ? 'dropping' : ''}`} {...dropOut}>
        {groups.length > 0 && ungrouped.length > 0 && <div className="history-subheading">{t('groups.ungrouped')}</div>}
        {ungrouped.map(item)}
        {!conversations.length && !groups.length && <p className="history-empty">{t('navigation.emptyHistory')}</p>}
      </div>
    </div>
  </>
}
