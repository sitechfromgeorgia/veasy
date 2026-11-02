---
name: formats
description: "Use when choosing or creating a show format for tbilisi.today Shorts (which look, caption design, voice, music and length a kind of video uses), or when asked what the engine can do. Examples: \"make an evening news format\", \"which captions should sports use\", \"list the options\""
---

# Formats (shows)

A format is a named set of choices; the engine renders any story in any format. Which show uses which format is
decided with the owner; this skill only explains the mechanics.

```bash
python -m tt_shorts.engine options   # looks, captions, voices (with the owner-approved ones), music, formats, scenes
```

## The choices

| Key | Values | Default |
|---|---|---|
| `look` | `auto` (by category), `editorial`, `kinetic`, `cards` | `auto` |
| `captions` | `page` (fixed two-line block), `roll` (three-line teleprompter) | `page` |
| `voice` | `family` (by category) or a preset: `plain`, `anchor`, `warm`, `clear` (approved), `firm`, `documentary` | `family` |
| `music` | `family` (by category), `off`, or a family: politics, economy, world, crime, sports, culture, tech, society | `family` |
| `platform` | the QR link's utm_source: `shorts`, `youtube`, `instagram`, `tiktok`, ... | `shorts` |
| `min_seconds`, `max_seconds` | the length window a render must land in | 18, 45 |

Built-in: `news` (all defaults) and `news-roll` (roll captions). By category, `auto` gives hard news `editorial`,
light news `kinetic`, service news `cards`; `family` voices give hard news `anchor`, people's news `warm`,
numbers and tech `clear`, sports `plain`.

## Add a show (no code change)

Create `formats/<name>.json` with only the keys that differ, then check it is accepted:
```json
{"label": "საღამოს ამბები", "about": "Evening wrap: calm, anchor voice, roll captions.",
 "look": "editorial", "captions": "roll", "voice": "anchor", "max_seconds": 40}
```
`python -m tt_shorts.engine options` fails loudly (exit 2) on a value the engine can't do. Render with
`--format <name>`; any key can still be overridden per render (`--captions page`).

## What a format can't change

The palette (brand v1.2), the safe zone, the news rules, the date/sources/link from the data, and the voices'
approval: a new voice preset or a new look is code (`voices.py`, `remotion/src`) and needs the owner's ear or eye
first.
