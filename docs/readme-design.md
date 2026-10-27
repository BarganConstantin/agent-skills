# README art direction and compatibility

*Original presentation for `BarganConstantin/agent-skills`, 27 October 2026.*

## Visual direction

**Editorial developer workbench**, not a generic AI-gradient banner. A dark ink-and-slate surface, precise typography, sharp warm-lime emphasis, deliberate negative space and an interface-style index communicate the four *actual* skills. The lead line—“Keep the context. Ship with evidence.”—connects handoffs, tests and the curated library without inventing usage metrics.

The banner was composed as **original local SVG source** (`assets/readme-hero.svg`), not a copied theme, external image, screenshot or generated adoption chart. The labels and descriptions should change when the catalog changes.

## GitHub rendering decisions

- Embed with `<img src="assets/readme-hero.svg" width="100%" alt="..."/>`, not unsafe `style`, scripts, iframes or remote JavaScript. GitHub sanitizes README HTML.
- SVG uses a fixed `viewBox` for responsive scaling, basic shapes, readable fallback font families, `<title>`/`<desc>`, and no external fonts/images/network calls.
- The signal on the workbench uses **SVG SMIL** rather than scripts or CSS keyframes. GitHub may proxy SVG and clients may differ in whether animation runs; the meaningful content must be present as static SVG text and shapes.
- Animation is decoration only and runs for **two slow cycles**, then stops. The core information is legible when paused or when animation is unsupported. This is a pragmatic fallback, **not a claim of complete reduced-motion media-query support**, which README sanitization cannot reliably preserve.
- The README itself remains semantic Markdown with links and copy/paste commands, so text search, accessibility, copying and navigating do not require SVG or motion. CI verifies link targets, local asset presence, non-executable SVG markup, descriptive image labels, and finite motion.

## Inspirations and boundaries

- [Awesome README](https://github.com/matiassingers/awesome-readme): expressive but useful project headers, meaningful screenshots, and quick navigation.
- [SVG Motion Cookbook](https://github.com/WaterTian/svg-motion-cookbook): proof that restrained script-free SMIL can animate README artwork under GitHub sanitization constraints. Our SVG geometry, copy, colors and composition are independent and not a copy of its examples.
- [Hallmark](https://github.com/Nutlope/hallmark): a clear anti-generic design philosophy. The original visual avoids fake testimonials, needless glows, giant emoji grids and imitation dashboards with fictional data.

**Do not claim a static preview is a real app screenshot**, or that aesthetic updates cause increased GitHub stars. The redesign changes communication, not independently measured adoption. Keep the four skill names and one real copy-paste demonstration current as functionality evolves.
