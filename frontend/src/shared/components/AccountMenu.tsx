import { useEffect, useRef, useState } from 'react'
import { ChevronsUpDown, LogOut, UserRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { AuthUser } from '../auth/AuthProvider'

interface Props {
  user: AuthUser
  onSignOut: () => void
}

function Avatar({ user, size }: { user: AuthUser; size: 'small' | 'large' }) {
  const [broken, setBroken] = useState(false)
  if (user.avatar_url && !broken) {
    // Google profile photos refuse requests that carry a referrer from other sites.
    return <img className={`avatar ${size}`} src={user.avatar_url} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)} />
  }
  return <span className={`avatar ${size}`} aria-hidden="true"><UserRound size={size === 'large' ? 20 : 16} /></span>
}

/** The signed-in account. Opens a menu; signing out is an explicit button inside it. */
export function AccountMenu({ user, onSignOut }: Props) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const name = user.full_name || user.email || t('account.unnamed')
  const role = t(`account.roles.${user.role}`, { defaultValue: user.role })

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === 'Escape' : !root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', close) }
  }, [open])

  return <div className="account" ref={root}>
    {open && <div className="account-menu" role="menu" aria-label={t('account.menu')}>
      <div className="account-menu-header">
        <Avatar user={user} size="large" />
        <div className="account-menu-identity">
          <strong>{name}</strong>
          {user.email && <span>{user.email}</span>}
          <span className={`role-badge ${user.role}`}>{role}</span>
        </div>
      </div>
      <button className="account-menu-item danger" role="menuitem" onClick={() => { setOpen(false); onSignOut() }}>
        <LogOut size={15} />{t('navigation.signOut')}
      </button>
    </div>}
    <button className="profile" onClick={() => setOpen(value => !value)} aria-haspopup="menu" aria-expanded={open}>
      <Avatar user={user} size="small" />
      <span className="profile-copy"><strong>{name}</strong><small>{role}</small></span>
      <ChevronsUpDown size={15} aria-hidden="true" />
    </button>
  </div>
}
