import { BookOpen, History, LogOut, MessageSquarePlus, Plus, Search, Settings, ShieldCheck, Sparkles, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { AuthUser } from '../auth/AuthProvider'
import type { ConversationSummary } from '../types/tax'

interface Props {
  activeConversation: string | null
  conversations: ConversationSummary[]
  user: AuthUser
  mobileOpen: boolean
  onNewChat: () => void
  onOpenConversation: (id: string) => void
  onSignOut: () => void
  onCloseMobile: () => void
}

export function AppSidebar({ activeConversation, conversations, user, mobileOpen, onNewChat, onOpenConversation, onSignOut, onCloseMobile }: Props) {
  const { t } = useTranslation()
  return <>
    <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><span /></div><span className="brand-name">taxora</span><button aria-label={t('navigation.closeNavigation')} className="icon-btn mobile-close" onClick={onCloseMobile}><X size={18} /></button></div>
      <button className="new-chat" onClick={onNewChat}><MessageSquarePlus size={17} /><span>{t('navigation.newConversation')}</span><Plus className="new-plus" size={16} /></button>
      <div className="nav-label">{t('navigation.workspace')}</div>
      <nav className="primary-nav" aria-label={t('navigation.workspace')}>
        <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Sparkles size={17} /><span>{t('navigation.taxAssistant')}</span></NavLink>
        <NavLink to="/regulations" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><BookOpen size={17} /><span>{t('navigation.regulationLibrary')}</span></NavLink>
        {user.role === 'admin' && <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><Settings size={17} /><span>{t('navigation.knowledgeAdmin')}</span></NavLink>}
      </nav>
      <div className="history-heading"><span>{t('navigation.recent')}</span><button aria-label={t('navigation.searchConversations')} title={t('navigation.searchConversations')} className="icon-btn"><Search size={15} /></button></div>
      <div className="history-list">{conversations.length ? conversations.map(item => <button key={item.id} className={`history-item ${activeConversation === item.id ? 'selected' : ''}`} onClick={() => onOpenConversation(item.id)}><History size={15} /><span>{item.title}</span></button>) : <p className="history-empty">{t('navigation.emptyHistory')}</p>}</div>
      <div className="sidebar-bottom"><div className="privacy-note"><ShieldCheck size={16} /><div><strong>{t('navigation.evidenceFirst')}</strong><span>{t('navigation.sourcesToVerify')}</span></div></div><button className="profile" onClick={onSignOut} title={t('navigation.signOut')}><div className="avatar">{(user.full_name || user.email || 'U').slice(0, 1).toUpperCase()}</div><span className="profile-copy"><strong>{user.full_name || user.email}</strong><small>{t('navigation.signedIn')}</small></span><LogOut size={17} aria-label={t('navigation.signOut')} /></button></div>
    </aside>
    {mobileOpen && <button className="mobile-scrim" aria-label={t('common.close')} onClick={onCloseMobile} />}
  </>
}
