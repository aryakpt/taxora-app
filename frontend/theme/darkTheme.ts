/**
 * Build-time dark theme.
 *
 * The stylesheets carry ~200 hand-picked light colors. Instead of duplicating every rule by hand, this PostCSS
 * plugin adds a `[data-theme="dark"]` twin after each rule that sets a color, with every color passed through
 * `toDark`: lightness is inverted in OKLCH along a measured curve (dark text on a light card stays readable as light
 * text on a dark card; cards sit slightly above the page; the sidebar lands exactly on DARKEST), neutrals take the
 * brand teal, and accents keep their hue.
 * New styles therefore get a dark version automatically. Hand-tuned exceptions live in
 * `src/shared/styles/themes/_dark.scss`; rules that already mention `data-theme` are left alone.
 */
import type { Declaration, Plugin, Rule } from 'postcss'

export const DARKEST = '#092328'

type Lch = { l: number; c: number; h: number; alpha: number }

const toLinear = (v: number) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
const toGamma = (v: number) => (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055)

function rgbToLch(r: number, g: number, b: number, alpha: number): Lch {
  const [lr, lg, lb] = [r, g, b].map(v => toLinear(v / 255))
  const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb)
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb)
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb)
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
  return { l: L, c: Math.hypot(A, B), h: Math.atan2(B, A), alpha }
}

function lchToRgb({ l: L, c, h }: Lch): [number, number, number] | null {
  const A = c * Math.cos(h)
  const B = c * Math.sin(h)
  const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
  const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
  const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3
  const rgb = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ]
  if (rgb.some(v => v < -0.0005 || v > 1.0005)) return null
  return rgb.map(v => Math.round(toGamma(Math.min(1, Math.max(0, v))) * 255)) as [number, number, number]
}

function parseHex(hex: string): [number, number, number, number] {
  let digits = hex.slice(1)
  if (digits.length <= 4) digits = [...digits].map(d => d + d).join('')
  const n = (i: number) => parseInt(digits.slice(i, i + 2), 16)
  return [n(0), n(2), n(4), digits.length === 8 ? n(6) / 255 : 1]
}

const hex2 = (n: number) => n.toString(16).padStart(2, '0')

function format(lch: Lch): string {
  let rgb = lchToRgb(lch)
  for (let c = lch.c; !rgb && c > 0; c -= 0.004) rgb = lchToRgb({ ...lch, c: Math.max(0, c) }) // into sRGB gamut
  const [r, g, b] = rgb ?? lchToRgb({ ...lch, c: 0 })!
  const alpha = lch.alpha < 1 ? hex2(Math.round(lch.alpha * 255)) : ''
  return `#${hex2(r)}${hex2(g)}${hex2(b)}${alpha}`
}

const base = rgbToLch(...parseHex(DARKEST))

/** Piecewise-linear lookup through [x, y] points sorted by x. */
function curve(points: [number, number][], x: number): number {
  if (x <= points[0][0]) return points[0][1]
  for (let i = 1; i < points.length; i++) {
    const [x1, y1] = points[i]
    if (x <= x1) {
      const [x0, y0] = points[i - 1]
      return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    }
  }
  return points[points.length - 1][1]
}

// Light-theme lightness -> dark-theme lightness (OKLCH). Measured on the stylesheets' own colors:
//   white cards and inputs (1.0)   -> 0.281  raised a little above the page
//   sidebar off-white (0.988)      -> 0.239  DARKEST
//   page canvas (0.979)            -> 0.254
//   hover fills (0.96)             -> 0.312
//   borders (0.93) / strong (0.87) -> 0.36 / 0.41
//   muted text (0.60-0.68)         -> 0.66-0.72
//   body text (0.47) / ink (0.29)  -> 0.82 / 0.935
const SURFACES: [number, number][] = [[0.2, 0.95], [0.29, 0.935], [0.386, 0.88], [0.471, 0.82], [0.596, 0.72],
  [0.682, 0.66], [0.728, 0.6], [0.874, 0.408], [0.93, 0.36], [0.96, 0.312], [0.979, 0.254]]
const SIDEBAR_BAND = 0.984 // 0.984..0.995: the sidebar's off-white
const CARD_BAND = 0.995 // above: white

function darkLightness(l: number): number {
  if (l >= CARD_BAND) return 0.281
  if (l >= SIDEBAR_BAND) return base.l
  return curve(SURFACES, l)
}

// Neutrals take the brand teal: saturated near the background, fading to a soft, slightly warm white for text.
// Hues in radians on the short arc: teal (212deg) -> green-grey (180deg), never through red.
const BASE_HUE = base.h < 0 ? base.h + 2 * Math.PI : base.h
const NEUTRAL_CHROMA: [number, number][] = [[0.26, base.c], [0.41, 0.036], [0.93, 0.01]]
const NEUTRAL_HUE: [number, number][] = [[0.5, BASE_HUE], [0.93, Math.PI]]

/** Below this chroma a color counts as grey: stricter for pale tints (a soft green or red is meant), looser
 * for the bluish greys used for text. */
const neutralBelow = (l: number) => (l > 0.85 ? 0.012 : l < 0.45 ? 0.045 : 0.03)

/** The dark-theme counterpart of one light-theme color. */
export function toDark(r: number, g: number, b: number, alpha = 1): string {
  const color = rgbToLch(r, g, b, alpha)
  if (alpha < 1 && color.l < 0.5) {
    // A shadow or scrim: stays dark, a little stronger so it still reads on a dark page.
    return format({ l: 0, c: 0, h: 0, alpha: Math.min(0.75, alpha * 2.5) })
  }
  const l = darkLightness(color.l)
  const neutral = color.c < neutralBelow(color.l)
  if (neutral) {
    return format({ l, c: curve(NEUTRAL_CHROMA, l), h: curve(NEUTRAL_HUE, l), alpha })
  }
  if (color.l > 0.85) {
    // A pale tint behind a status or a selection (soft green, soft red, soft gold): a deep version of its hue.
    // Deep greens read as olive, so green tints lean halfway to the brand teal.
    const hue = color.h < 0 ? color.h + 2 * Math.PI : color.h
    const greenish = hue > (2 * Math.PI) / 3 && hue < BASE_HUE
    return format({ l: l + 0.02, c: Math.min(0.04, color.c * 2.2), h: greenish ? (hue + BASE_HUE) / 2 : hue, alpha })
  }
  // Accents (brand green, gold, error red, navy mark) keep their hue and most of their brightness.
  const vivid = Math.min(1, color.c / 0.1)
  return format({ l: l + (Math.max(color.l, 0.68) - l) * vivid, c: color.c, h: color.h, alpha })
}

const NAMED: Record<string, string> = { white: '#ffffff', black: '#000000' }
const COLOR = /#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})\b|\brgba?\(([^)]+)\)|\b(?:white|black)\b/gi

export function darkenValue(value: string): string {
  return value.replace(COLOR, (match, rgbArgs: string | undefined) => {
    if (rgbArgs) {
      const parts = rgbArgs.split(/[\s,/]+/).filter(Boolean).map(part =>
        part.endsWith('%') ? parseFloat(part) / 100 : parseFloat(part))
      const [r, g, b, a = 1] = parts
      return toDark(r, g, b, a)
    }
    const hex = NAMED[match.toLowerCase()] ?? match
    return toDark(...parseHex(hex))
  })
}

const SKIP_PROPERTIES = /^(?:font|transition|animation|transform|grid|content)/i

function themedSelector(selector: string): string {
  const trimmed = selector.trim()
  if (trimmed === ':root' || trimmed === 'html') return `${trimmed}[data-theme="dark"]`
  if (/^(?::root|html)\b/.test(trimmed)) return trimmed.replace(/^(:root|html)/, '$1[data-theme="dark"]')
  return `[data-theme="dark"] ${trimmed}`
}

export function darkTheme(): Plugin {
  return {
    postcssPlugin: 'taxora-dark-theme',
    OnceExit(root) {
      root.walkRules((rule: Rule) => {
        if (rule.selector.includes('data-theme')) return
        if (rule.parent?.type === 'atrule' && /keyframes$/i.test((rule.parent as { name: string }).name)) return
        const changed: Declaration[] = []
        rule.each(node => {
          if (node.type !== 'decl' || SKIP_PROPERTIES.test(node.prop) || node.value.includes('url(')) return
          const value = darkenValue(node.value)
          if (value !== node.value) changed.push(node.clone({ value }))
        })
        if (!changed.length) return
        const twin = rule.clone({ selectors: rule.selectors.map(themedSelector) })
        twin.removeAll()
        twin.append(...changed)
        rule.after(twin)
      })
    },
  }
}
darkTheme.postcss = true
