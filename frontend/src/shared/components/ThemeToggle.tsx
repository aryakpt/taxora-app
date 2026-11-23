import { Moon, Sun } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { setTheme, useTheme } from '../theme/theme'

export function ThemeToggle() {
  const { t } = useTranslation()
  const theme = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  const label = t(next === 'dark' ? 'theme.useDark' : 'theme.useLight')
  return <button type="button" className="theme-toggle" aria-label={label} title={label} onClick={() => setTheme(next)}>
    {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
  </button>
}
