import { useSyncExternalStore } from 'react'

/** Light or dark. With no saved choice the app follows the system setting, live. */
export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'taxora-theme'
// Same values as the canvas colors in the stylesheets; used for the browser's address bar.
const THEME_COLORS: Record<Theme, string> = { light: '#f7f8fa', dark: '#092328' }
const systemDark = window.matchMedia('(prefers-color-scheme: dark)')
const listeners = new Set<() => void>()

function saved(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch { return null }
}

let current: Theme = saved() ?? (systemDark.matches ? 'dark' : 'light')

function apply(theme: Theme) {
  current = theme
  document.documentElement.dataset.theme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLORS[theme])
  listeners.forEach(listener => listener())
}

apply(current)
systemDark.addEventListener('change', event => { if (!saved()) apply(event.matches ? 'dark' : 'light') })

export function setTheme(theme: Theme) {
  try { localStorage.setItem(STORAGE_KEY, theme) } catch { /* private mode: still switch for this visit */ }
  apply(theme)
}

export function useTheme(): Theme {
  return useSyncExternalStore(listener => { listeners.add(listener); return () => listeners.delete(listener) }, () => current)
}
