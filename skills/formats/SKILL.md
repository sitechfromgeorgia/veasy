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

## The choices

| Key | Values | Default |
|---|---|---|
| `look` | `auto` (by category), `editorial`, `kinetic`, `cards` | `auto` |
| `captions` | `page` (fixed two-line block), `roll` (three-line teleprompter) | `page` |
| `transition` | `auto` (varied per video among those that suit the look), `cut`, `line`, `panel`, `wipe`, `slide`, `push`, `dot` (an iris from the header's progress dot) | `auto` |
| `outro` | `card` (the end card: logo, QR, link, CTA), `overlay` (no end card: a QR/link/CTA chip slides in over the last scene), `loop` (the chip, then the last 0.5 s cross-fade into the hook's first frame: a seamless replay) | `card` |
| `voice` | `family` (by category, from the brand pack) or a preset: `plain`, `anchor`, `warm`, `clear` (approved for tbilisi.today), `firm`, `documentary`, or a pack's own (`sitech`) | `family` |
| `music` | `family` (by category), `off`, or a family: politics, economy, world, crime, sports, culture, tech, society | `family` |
| `platform` | the QR link's utm_source: `shorts`, `youtube`, `instagram`, `tiktok`, ... | `shorts` |
| `min_seconds`, `max_seconds` | the length window a render must land in | 18, 45 |

Built-in: `news` (all defaults) and `news-roll` (roll captions). `auto` and `family` follow the story's brand pack
(`options --brand <name>` shows its table). tbilisi.today: hard news `editorial` + `anchor`, light news `kinetic`,
service news `cards`; people's news `warm`, numbers and tech `clear`, sports `plain`. SiTech: its own `sitech`
voice (Charon) for every family. A format works for every brand; a pack's own voice only for that pack.

## Variety comes on its own

Inside a format, every video gets its own hook layout (stack, lead, blocks, underline), background motif (grid,
diagonal, dots, rules, plain), entrance (rise, slide, reveal, scale), transition (when `auto`) and music loop
(four per family): the least used lately for the brand (`options` → `variety`). So a format doesn't need to vary
these by hand; fix one in a format only when a show must always look one way (e.g. `"transition": "cut"`).

## Built for the swipe and the loop (`tt_shorts/swipe.py`)

The first frame decides whether people swipe away, and Shorts count every replay as a view. In every format:
- the hook is fully readable at frame 0 (it only settles a few px), and `qa` fails a render whose frame 0 is empty;
- the voice starts at once: leading silence is cut to 0.12 s, and the captions and cuts move with it.

`outro` is the one choice here, and an A/B arm for later (ROADMAP D8):
- `card`: today's ending, 1.6 s after the last word.
- `overlay`: the story's `end` scene is dropped; the scene before it runs to the end. The chip comes in with the
  end scene's words (the call to action), at least 3 s before the end, inside the safe zone, and the scene shrinks
  to make room. The voice is the same; only the tail after the last word is shorter (1.0 s instead of 1.6 s).
- `loop`: like `overlay`, with a 0.8 s tail whose last 0.5 s cross-fades into the hook. The music keeps one level
  to the last frame (no fade-out) and the ticker comes back to where it started, so the replay has no seam.

The story JSON doesn't change: keep writing the `end` scene; the outro decides whether it is shown.

## Add a show (no code change)

Create `formats/<name>.json` with only the keys that differ, then check it is accepted:
```json
{"label": "საღამოს ამბები", "about": "Evening wrap: calm, anchor voice, roll captions.",
 "look": "editorial", "captions": "roll", "voice": "anchor", "max_seconds": 40}
```
A looping show is one key: `{"label": "ამბავი: უწყვეტი", "about": "Ends where it began.", "outro": "loop"}`.
`python -m tt_shorts.engine options` fails loudly (exit 2) on a value the engine can't do. Render with
`--format <name>`; any key can still be overridden per render (`--captions page`).

## What a format can't change

The palette, logo and words (the brand pack's, `veasy:brands`), the safe zone, the news rules, the
date/sources/link from the data, and the voices' approval: a new voice preset or a new look is code or a pack
(`voices.py`, a pack's `voices`, `remotion/src`) and needs the owner's ear or eye first.
