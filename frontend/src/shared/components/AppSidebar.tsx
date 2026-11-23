import { BookOpen, Settings, ShieldCheck, SquarePen, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { canReview, type AuthUser } from '../auth/AuthProvider'
import { AccountMenu } from './AccountMenu'
import { SidebarResizer } from './SidebarResizer'
import { ConversationHistory, type HistoryActions } from './ConversationHistory'
import type { ConversationGroup, ConversationSummary } from '../types/tax'

interface Props extends HistoryActions {
  activeConversation: string | null
  conversations: ConversationSummary[]
  groups: ConversationGroup[]
  user: AuthUser
  mobileOpen: boolean
  onNewChat: () => void
  onSignOut: () => void
  onCloseMobile: () => void
  width: number
  onResize: (width: number) => void
  onResizeEnd: (width: number) => void
}

export function AppSidebar({ activeConversation, conversations, groups, user, mobileOpen, onNewChat, onSignOut, onCloseMobile, width, onResize, onResizeEnd, ...historyActions }: Props) {
  const { t } = useTranslation()
  return <>
    <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><span /></div><span className="brand-name">taxora</span><button aria-label={t('navigation.closeNavigation')} className="icon-btn mobile-close" onClick={onCloseMobile}><X size={18} /></button></div>
      <button className="new-chat" onClick={onNewChat}><SquarePen size={17} aria-hidden="true" /><span>{t('navigation.newConversation')}</span></button>
      <div className="nav-label">{t('navigation.workspace')}</div>
      <nav className="primary-nav" aria-label={t('navigation.workspace')}>
        <NavLink to="/regulations" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><BookOpen size={17} /><span>{t('navigation.regulationLibrary')}</span></NavLink>
        {canReview(user) && <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Settings size={17} /><span>{t('navigation.knowledgeAdmin')}</span></NavLink>}
      </nav>
      <ConversationHistory activeConversation={activeConversation} conversations={conversations} groups={groups} {...historyActions} />
      <div className="sidebar-bottom"><div className="privacy-note"><ShieldCheck size={16} /><div><strong>{t('navigation.evidenceFirst')}</strong><span>{t('navigation.sourcesToVerify')}</span></div></div><AccountMenu user={user} onSignOut={onSignOut} /></div>
      <SidebarResizer width={width} onResize={onResize} onCommit={onResizeEnd} />
    </aside>
    {mobileOpen && <button className="mobile-scrim" aria-label={t('common.close')} onClick={onCloseMobile} />}
  </>
}
