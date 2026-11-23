# Shared styles and Taxora design system

`main.scss` is the only stylesheet entrypoint imported by `main.tsx`. Styles are grouped into Sass partials:

- `abstracts/_tokens.scss` — shared semantic colors, typography, spacing, radii, and motion tokens.
- `base/_reset.scss` — document defaults and accessible focus treatment.
- `base/_typography.scss` — shared responsive type scale; adjust the centralized sizes here when tuning reading comfort.
- `layout/_shell.scss` — application-level layout primitives.
- `components/_navigation.scss` — shared navigation styles.
- `utilities/_motion.scss` — reduced-motion support.
- `themes/_dark.scss` — hand-tuned dark-theme exceptions (filled buttons, login backdrop).
- `legacy/_application.scss` — existing UI rules retained during migration so the refactor does not redesign existing screens.

New styles should use Sass modules (`@use`) and semantic tokens rather than adding unrelated raw values. Move rules from `legacy/_application.scss` into their feature/component partial as they are next edited; avoid adding new rules to the legacy partial. Sass variables are for compile-time decisions; CSS custom properties emitted from `_tokens.scss` are available at runtime.

## Dark theme

The dark theme is generated at build time by the PostCSS plugin in `frontend/theme/darkTheme.ts`: every rule that sets a color gets a `[data-theme="dark"]` twin whose colors have their lightness inverted in OKLCH (the darkest surface is `#092328`), so new styles get a dark version without extra work. Check new screens in both themes; when a generated color looks wrong, override it in `themes/_dark.scss`. The choice is stored in `localStorage` (`taxora-theme`); with no choice the app follows the system setting.
