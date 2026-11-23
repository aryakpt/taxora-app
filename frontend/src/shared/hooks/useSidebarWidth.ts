import { useCallback, useState } from 'react'

export const SIDEBAR_DEFAULT_WIDTH = 258
export const SIDEBAR_MIN_WIDTH = 200
export const SIDEBAR_MAX_WIDTH = 420
const STORAGE_KEY = 'taxora-sidebar-width'

export const clampSidebarWidth = (width: number) =>
  Math.round(Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width)))

function stored(): number {
  try {
    const value = Number(localStorage.getItem(STORAGE_KEY))
    return value ? clampSidebarWidth(value) : SIDEBAR_DEFAULT_WIDTH
  } catch {
    return SIDEBAR_DEFAULT_WIDTH  // storage can be unavailable (private mode, blocked site data)
  }
}

/** The desktop sidebar width chosen by dragging its edge, remembered in this browser. */
export function useSidebarWidth() {
  const [width, setWidth] = useState(stored)

  const resize = useCallback((next: number) => setWidth(clampSidebarWidth(next)), [])

  const save = useCallback((value: number) => {
    try { localStorage.setItem(STORAGE_KEY, String(clampSidebarWidth(value))) } catch { /* not remembered, still works */ }
  }, [])

  return { width, resize, save }
}
