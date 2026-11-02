---
name: formats
description: "Use when choosing or creating a show format for Veasy videos (which look, caption design, voice, music and length a kind of video uses), or when asked what the engine can do. Examples: \"make an evening news format\", \"which captions should sports use\", \"list the options\""
---

# Formats (shows)

A format is a named set of choices; the engine renders any story in any format. Which show uses which format is
decided with the owner; this skill only explains the mechanics.

```bash
python -m tt_shorts.engine options   # looks, captions, voices (with the owner-approved ones), music, formats, scenes
```
(`options` also lists `areas`: the codes a `where` scene may name, `ge:<region>`. That is a story field, not a
format choice. The map itself needs no format key; see `veasy:write-script`.)

## The choices

| Key | Values | Default |
|---|---|---|
| `look` | `auto` (by category), `editorial`, `kinetic`, `cards` | `auto` |
| `captions` | `page` (fixed two-line block), `roll` (three-line teleprompter) | `page` |
| `transition` | `auto` (varied per video among those that suit the look), `cut`, `line`, `panel`, `wipe`, `slide`, `push`, `dot` (an iris from the header's progress dot) | `auto` |
| `voice` | `family` (by category, from the brand pack) or a preset: `plain`, `anchor`, `warm`, `clear` (approved for tbilisi.today), `firm`, `documentary`, or a pack's own (`sitech`) | `family` |
| `music` | `family` (by category), `off`, or a family: politics, economy, world, crime, sports, culture, tech, society | `family` |
| `platform` | the QR link's utm_source: `shorts`, `youtube`, `instagram`, `tiktok`, ... | `shorts` |
| `min_seconds`, `max_seconds` | the length window a render must land in | 18, 45 |

Built-in: `news` (all defaults) and `news-roll` (roll captions); `formats/explainer.json` (25-45 s) is the
default of the explainer and law programs (a program names its format: `veasy:programs`). `auto` and `family` follow the story's brand pack
(`options --brand <name>` shows its table). tbilisi.today: hard news `editorial` + `anchor`, light news `kinetic`,
service news `cards`; people's news `warm`, numbers and tech `clear`, sports `plain`. SiTech: its own `sitech`
voice (Charon) for every family. A format works for every brand; a pack's own voice only for that pack.

## Variety comes on its own

Inside a format, every video gets its own hook layout (stack, lead, blocks, underline), background motif (grid,
diagonal, dots, rules, plain), entrance (rise, slide, reveal, scale), transition (when `auto`) and music loop
(four per family): the least used lately for the brand (`options` → `variety`). So a format doesn't need to vary
these by hand; fix one in a format only when a show must always look one way (e.g. `"transition": "cut"`).

## Add a show (no code change)

Create `formats/<name>.json` with only the keys that differ, then check it is accepted:
```json
{"label": "საღამოს ამბები", "about": "Evening wrap: calm, anchor voice, roll captions.",
 "look": "editorial", "captions": "roll", "voice": "anchor", "max_seconds": 40}
```
`python -m tt_shorts.engine options` fails loudly (exit 2) on a value the engine can't do. Render with
`--format <name>`; any key can still be overridden per render (`--captions page`).

## What a format can't change

The palette, logo and words (the brand pack's, `veasy:brands`), the safe zone, the news rules, the
date/sources/link from the data, and the voices' approval: a new voice preset or a new look is code or a pack
(`voices.py`, a pack's `voices`, `remotion/src`) and needs the owner's ear or eye first.
