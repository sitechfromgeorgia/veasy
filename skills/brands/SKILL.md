---
name: brands
description: "Use when a video should look and sound like a client (colors, themes such as light or dark, logo, link, footer, voice, words), when adding a new client or a new theme to Veasy, or when asked which brands Veasy can make videos for. Examples: \"make this as a SiTech video\", \"make it on a white background\", \"add a brand for our new client\", \"why is the button orange\""
---

# Brand packs

Everything that makes a video one client's and not another's is data in `brands/<name>/brand.json`; the engine
has no client in its code. Shipped: `tbilisi-today` (default; black, white, one red, the t-mark) and `sitech`
(coal and paper, SiTech orange, the SiTech logo, the Charon voice). `brands/_ka` is a base: Georgian dates and
words, Tbilisi time, FiraGO, the news categories; a pack says `"extends": "_ka"` and overrides what differs.

```bash
python -m tt_shorts.engine options                  # "brands": every pack; the categories of the default one
python -m tt_shorts.engine options --brand sitech   # that pack's categories, looks, voices (its own are marked)
```
A story picks its pack with `"brand": "sitech"` (or `write --brand`, `queue add --brand`). Without one it is
tbilisi-today.

## What a pack holds

| Key | What |
|---|---|
| `label`, `wordmark` | the name in the ticker; the wordmark text and its accent character (`.` of tbilisi.today) |
| `themes`, `default_theme` | the pack's palettes: `{"dark": {"colors": {...}}, "light": {"colors": {...}, "logo": {...}, "allowed": false}}`; below. A pack with a plain `colors` has one theme |
| `fonts` | 400/500/600/700 woff2 (one family; captions are measured with the 700) |
| `logo` | `{"kind": "tmark"}`, or `{"kind": "svg", "header": "logo-horizontal.svg", "end": "logo-stacked.svg"}` (the SVGs carry the name) |
| `link` | `display` (as shown) and `qr` (the tracked URL; must contain `{id}`, may contain `{platform}`) |
| `footer` | `{"text": ..., "strong": ...}`, the quiet line next to the link |
| `ctas` | the end card's calls to action, rotated by story |
| `categories`, `family_by_category`, `default_family` | the category word; the family picks look, voice and music |
| `look_by_family`, `voice_by_family` | editorial / kinetic / cards; a voice preset per family |
| `voices` | the pack's own presets (`{"label", "voice", "style"}`), usable only by this pack |
| `say` | spoken forms of the pack's own names (`"SiTech": "საი-თეჩი"`), under every story's `say` |
| `strings`, `months`, `weekdays`, `utc_offset_hours` | the words on screen and the date |
| `media` | the media layer (`tt_shorts/assets.py`, news rule N13): `providers`, the order a scene's picture is searched in (`openverse`, `commons`, `pexels`, `pixabay`; `[]`: no stock pictures for this pack); `official` and `own`, the domains a screenshot may come from (`_ka`: matsne.gov.ge, gov.ge, parliament.ge; a pack: its own site). `strings.illustrative` („საილუსტრაციო") is the label every illustrative picture carries, `strings.media_credit` the credit line (`{author}`, `{licence}`, `{source}`) |
| `package` | `engine package`'s words (`veasy:package`): `more` (a link line with `{url}`), `link_in_bio`, and `hashtags` (3+, the pack's own after the category's tag; `_ka` has the words, a pack sets its tags) |

## Themes (a pack on another ground)

Owner, 2026-11-03: not only on a night background; a white one and others too. A theme is one full palette:
`colors` = canvas, panel, ink, muted, accent, line, lineStrong, grid, ticker, waiting, markBg, onAccent (the text
on the accent button), markInk (the t of the t-mark; default white); `#RRGGBB` for the solid ones, `rgba()` for
the lines and the dimmed ink. Optional: `logo` (`{"header": ..., "end": ...}`, an svg pack's files for that ground:
a white logo needs a dark one on paper), `allowed` (default true), `label`, `about`.

| Pack | Themes |
|---|---|
| `tbilisi-today` | `dark` (default, brand v1.2) · `light` (slate paper #F8FAFC, night ink, the same red; the mark unchanged): **allowed false** until the owner approves it |
| `sitech` | `dark` (default: coal, paper ink, orange) · `light` (paper #F1EDE4, coal ink, orange; `logo-*-coal.svg`, the white logo recolored) |

Every theme is checked on load (`brand.CONTRAST`, WCAG ratios): ink on canvas and on panel 7:1, muted 4.5:1, the
accent dot 2:1 against both, the button's text 3:1, the captions (spoken words 4.5:1 on the box over an ink block,
waiting words 3:1 on the box), the t-mark 3:1. A theme that fails names the pair and the ratio. Then every render's
layout probe judges each text against what is really under it (`probe contrast`), so a theme can't put dark on dark
or light on light anywhere (icons, map, drawings, chips, captions).

Choosing one: a format's or `--theme`'s `default` (the pack's default theme), `auto` (variety alternates the
allowed themes) or a name (`veasy:formats`). The QR is always dark on light: on a light theme it is the ink on
the canvas. Composed films (HyperFrames) get the theme's tokens in `brand.css` and `frame.md` (`--theme`).

To add a theme: a new entry under `themes` (copy the closest), `options --brand <name>` to see it load, then
`probe <story> --look all --theme <name> --stills <dir>` and the owner's eye; `"allowed": false` until then.

## Add a client (automated brand book intake)

Use the brand intake tool to draft and validate a pack from any source in seconds:
```bash
python -m tt_shorts.engine brand new <name> --from <url|pdf|design.md|frame.md>
```
Tool `veasy_brand` (`action: "new", name: "<name>", from: "<source>"`).
1. Automatically parses the source (a brand page URL, PDF, DTCG design tokens, or `frame.md`).
2. Extracts and balances palettes for dark and light themes, ensuring all WCAG contrast floors pass.
3. Writes `brands/<name>/brand.json` extending `_ka` with fonts, wordmark, links, footers and CTAs.
4. Validates the pack against `brand.py` and renders contact sheets (`brand-<name>-dark.plan.jpg`, `brand-<name>-light.plan.jpg`) for visual inspection.

Manual pack setup remains supported:
1. `brands/<name>/brand.json` with `"name": "<name>"`, `"extends": "_ka"` and the keys that differ; logo SVGs and
   fonts in the same folder (paths starting with `assets/` are Veasy's shared ones).
2. `python -m tt_shorts.engine options --brand <name>` and `doctor`: a missing key, an unknown family, look or
   voice, or a missing file fails here, before any render.
3. A still on a sample story (`still <story> --engine silent`) and the owner's eye before the first real video.

The rules a pack can't change: one accent color used for the dot, an active state and the button, never for text;
no shadows; the safe zone; the source and the time always on screen; news rules for news; readable contrast in
every theme.
