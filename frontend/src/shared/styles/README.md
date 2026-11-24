# Shared styles and Taxora design system

`main.scss` is the only stylesheet entrypoint imported by `main.tsx`. Styles are grouped into Sass partials:

- `abstracts/_tokens.scss` — design tokens: semantic colors, type scale, elevation, spacing, radii, motion, breakpoints and their mixins.
- `base/_reset.scss` — document defaults and accessible focus treatment.
- `base/_typography.scss` — shared responsive type scale; adjust the centralized sizes here when tuning reading comfort.
- `layout/_shell.scss` — application-level layout primitives.
- `layout/_responsive.scss` — device fit: dynamic viewport height, safe areas, 16px fields on touch screens, small phones, landscape phones.
- `components/_navigation.scss` — shared navigation styles.
- `utilities/_motion.scss` — reduced-motion support.
- `themes/_dark.scss` — hand-tuned dark-theme exceptions (filled buttons, login backdrop).
- `legacy/_application.scss` — existing UI rules retained during migration so the refactor does not redesign existing screens.

New styles should use Sass modules (`@use`) and semantic tokens rather than adding unrelated raw values. Move rules from `legacy/_application.scss` into their feature/component partial as they are next edited; avoid adding new rules to the legacy partial. Sass variables are for compile-time decisions; CSS custom properties emitted from `_tokens.scss` are available at runtime.

## Dark theme

The dark theme is generated at build time by the PostCSS plugin in `frontend/theme/darkTheme.ts`: every rule that sets a color gets a `[data-theme="dark"]` twin whose colors have their lightness inverted in OKLCH (the darkest surface is `#092328`), so new styles get a dark version without extra work. Check new screens in both themes; when a generated color looks wrong, override it in `themes/_dark.scss`. The choice is stored in `localStorage` (`taxora-theme`); with no choice the app follows the system setting.

## Tokens, not values

Components use tokens only — no hex colors, no `px` font sizes:

- **Color:** `var(--color-text|text-body|text-secondary|text-tertiary|text-brand…)`, `var(--color-surface…)`, `var(--color-border…)`, `var(--color-action…)`, and status pairs (`--color-success-text` on `--color-success-surface`, likewise `warning`, `danger`, `info`). Text tokens are measured at ≥ 4.5:1 on the page and on cards.
- **Type:** `var(--font-size-xs)` (12px) … `var(--font-size-5xl)`, in `rem` so the reader's text-size setting applies; `2xl` and up are fluid (`clamp`), so headings need no per-breakpoint sizes.
- **Elevation:** `var(--shadow-xs|sm|md|lg|xl|drawer)`.
- **Breakpoints:** `@include below('xs'|'sm'|'md'|'lg')`, `@include above(…)`, `@include touch`, and `@include drawer-layout` / `sidebar-layout` (the sidebar becomes a drawer at ≤ 800px wide or ≤ 500px tall). Add `@use '../abstracts/tokens' as *;` to use them.

A new color or size belongs in `_tokens.scss` first. The dark theme follows the tokens automatically; set a dark value by hand in `themes/_dark.scss` only when the generated one fails contrast or looks wrong.
