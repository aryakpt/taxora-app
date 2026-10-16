# Shared styles and Taxora design system

`main.scss` is the only stylesheet entrypoint imported by `main.tsx`. Styles are grouped into Sass partials:

- `abstracts/_tokens.scss` — shared semantic colors, typography, spacing, radii, and motion tokens.
- `base/_reset.scss` — document defaults and accessible focus treatment.
- `base/_typography.scss` — shared responsive type scale; adjust the centralized sizes here when tuning reading comfort.
- `layout/_shell.scss` — application-level layout primitives.
- `components/_navigation.scss` — shared navigation styles.
- `utilities/_motion.scss` — reduced-motion support.
- `legacy/_application.scss` — existing UI rules retained during migration so the refactor does not redesign existing screens.

New styles should use Sass modules (`@use`) and semantic tokens rather than adding unrelated raw values. Move rules from `legacy/_application.scss` into their feature/component partial as they are next edited; avoid adding new rules to the legacy partial. Sass variables are for compile-time decisions; CSS custom properties emitted from `_tokens.scss` are available at runtime.
