import { CircleHelp, Menu, PanelLeftClose } from 'lucide-react'
import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from './LanguageSwitcher'
import { HelpDialog } from './HelpDialog'

interface Props { onToggleSidebar: () => void; onOpenMobile: () => void }

export function AppHeader({ onToggleSidebar, onOpenMobile }: Props) {
  const { pathname } = useLocation()
  const { t } = useTranslation()
  const [helpOpen, setHelpOpen] = useState(false)
  const label = pathname === '/regulations' ? t('navigation.regulationLibrary') : pathname === '/admin' ? t('navigation.knowledgeAdmin') : t('navigation.taxAssistant')
  return <header className="topbar"><div className="topbar-left"><button aria-label={t('navigation.openNavigation')} className="icon-btn mobile-menu" onClick={onOpenMobile}><Menu size={19} /></button><button aria-label={t('navigation.toggleSidebar')} className="icon-btn desktop-collapse" onClick={onToggleSidebar}><PanelLeftClose size={18} /></button><span className="breadcrumb">{t('common.workspace')}</span><span className="crumb-sep">/</span><span className="breadcrumb-current">{label}</span></div><div className="topbar-right"><LanguageSwitcher /><button className="help-btn" aria-label={t('common.help')} title={t('common.help')} aria-haspopup="dialog" onClick={() => setHelpOpen(true)}><CircleHelp size={18} /></button></div>{helpOpen && <HelpDialog onClose={() => setHelpOpen(false)} />}</header>
}
