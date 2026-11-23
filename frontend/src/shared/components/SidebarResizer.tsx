import { useRef, type KeyboardEvent, type PointerEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { SIDEBAR_DEFAULT_WIDTH, SIDEBAR_MAX_WIDTH, SIDEBAR_MIN_WIDTH } from '../hooks/useSidebarWidth'

interface Props {
  width: number
  onResize: (width: number) => void
  onCommit: (width: number) => void
}

const KEY_STEP = 16

/** Drag handle on the sidebar's right edge. Pointer, keyboard (arrows, Home, End), and double-click to reset. */
export function SidebarResizer({ width, onResize, onCommit }: Props) {
  const { t } = useTranslation()
  const latest = useRef(width)
  latest.current = width

  function startDrag(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return
    event.preventDefault()
    const handle = event.currentTarget
    handle.setPointerCapture(event.pointerId)
    const left = handle.parentElement?.getBoundingClientRect().left ?? 0
    document.body.classList.add('sidebar-resizing')

    const move = (moveEvent: globalThis.PointerEvent) => onResize(moveEvent.clientX - left)
    // Save the width at the release point. The rendered width can still be one move behind, which saved
    // 330 for a drag that ended at 340.
    const end = (endEvent: globalThis.PointerEvent) => {
      handle.removeEventListener('pointermove', move)
      handle.removeEventListener('pointerup', end)
      handle.removeEventListener('pointercancel', end)
      document.body.classList.remove('sidebar-resizing')
      const final = endEvent.type === 'pointerup' ? endEvent.clientX - left : latest.current
      onResize(final)
      onCommit(final)
    }
    handle.addEventListener('pointermove', move)
    handle.addEventListener('pointerup', end)
    handle.addEventListener('pointercancel', end)
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const next = { ArrowLeft: width - KEY_STEP, ArrowRight: width + KEY_STEP, Home: SIDEBAR_MIN_WIDTH, End: SIDEBAR_MAX_WIDTH }[event.key]
    if (next === undefined) return
    event.preventDefault()
    onResize(next)
    onCommit(next)
  }

  function reset() {
    onResize(SIDEBAR_DEFAULT_WIDTH)
    onCommit(SIDEBAR_DEFAULT_WIDTH)
  }

  return <div
    className="sidebar-resizer"
    role="separator"
    aria-orientation="vertical"
    aria-label={t('navigation.resizeSidebar')}
    aria-valuemin={SIDEBAR_MIN_WIDTH}
    aria-valuemax={SIDEBAR_MAX_WIDTH}
    aria-valuenow={width}
    tabIndex={0}
    title={t('navigation.resizeSidebarHint')}
    onPointerDown={startDrag}
    onKeyDown={onKeyDown}
    onDoubleClick={reset}
  />
}
