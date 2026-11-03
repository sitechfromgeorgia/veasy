---
name: formats
description: "Use when choosing or creating a show format for Veasy videos (which look, caption design, voice, music and length a kind of video uses), or when asked what the engine can do. Examples: \"make an evening news format\", \"which captions should sports use\", \"list the options\""
---

# Formats (shows)

A format is a named set of choices; the engine renders any story in any format. Which show uses which format is
decided with the owner; this skill only explains the mechanics.

```bash
python -m tt_shorts.engine options                           # full options (all choices, scenes, brushes, icons)
python -m tt_shorts.engine options --section summary         # compact 1 KB overview: brands, formats, looks, voices, sections
python -m tt_shorts.engine options --section formats         # inspect only formats
```
(`options` also lists `areas`: the codes a `where` scene may name, `ge:<region>`. That is a story field, not a
format choice. The map itself needs no format key; see `veasy:write-script`.)

## The choices

| Key | Values | Default |
|---|---|---|
| `look` | `auto` (by category), `editorial`, `kinetic`, `cards` | `auto` |
| `captions` | `page` (fixed two-line block), `roll` (three-line teleprompter), `keyword` (the page's lines in a dark box, the spoken word lit, and per page one keyword code picks: the scene's em phrase, else a number, else a name from the story, drawn in the pack's `design.keyword` style: tbilisi.today an accent underline, SiTech its orange) | `page` |
| `transition` | `auto` (varied per video among those that suit the look), `cut`, `line`, `panel`, `wipe`, `slide`, `push`, `dot` (an iris from the header's progress dot), `meter` (equaliser bars in ink rise over the old scene and fall away from the new one) | `auto` |
| `beats` | `on` (a change inside every scene each 1.5-3 s on the words: items and labels come in when said, quotes and points light up a phrase a beat, the hook's rule, a stat's cells, a timeline's run and a map's camera step on), `off` (each scene's own stagger) | `on` |
| `chapters` | `off`, `on` ("01 / 03" and a segmented bar where the progress rule was; chapters of 3+ scenes by code, the hook in chapter 1, a digest's chapter cards opening its stories; none when a video can't make two), `auto` (on from 40 s) | `off` |
| `outro` | `card` (the end card: logo, QR, link, CTA), `overlay` (no end card: a QR/link/CTA chip slides in over the last scene), `loop` (the chip, then the last 0.5 s cross-fade into the hook's first frame: a seamless replay) | `card` |
| `voice` | `family` (by category, from the brand pack) or a preset: `plain`, `anchor`, `warm`, `clear` (approved for tbilisi.today), `firm`, `documentary`, or a pack's own (`sitech`) | `family` |
| `music` | `family` (by category), `off`, or a family: politics, economy, world, crime, sports, culture, tech, society | `family` |
| `sfx` | `off`, `on`: short sound effects on the timeline (`tt_shorts/sfx.py`): a whoosh on a cut (a click on a plain `cut`), a pop when a mark or the outro chip lands, ticks while a stat counts and a soft thud as it settles, a blip as each bar grows. Synthesized by `tools/compose_sfx.py`; one constant level under the voice, no ducking, no risers; mixed by ffmpeg, so it is the same in every engine | `off` |
| `platform` | the QR link's utm_source: `shorts`, `youtube`, `instagram`, `tiktok`, ... | `shorts` |
| `theme` | `default` (the pack's default theme: today's look, nothing changes), `auto` (varied per video among the pack's allowed themes, least used lately), or a theme's name: `dark`, `light` (every pack the format is used with must have it) | `default` |
| `min_seconds`, `max_seconds` | the length window a render must land in | 18, 45 |
| `engine` (optional) | the film engine: `remotion` (the brush kit) or `hyperframes` (a composed film, `veasy:compose`); a director's or program's wins over the format's, the format's over the pack's | remotion |
| `review` (optional) | composed films only: `always` (held for a person) or `until:<n>` (held until the brand has n approved in a row); a format's wins over the program's | always |

`formats/story.json` is the `story` program's (18-45 s, the culture music bed, engine hyperframes).
`engine options` → `film_engines` lists who sets which engine.

Built-in: `news` (all defaults) and `news-roll` (roll captions); `formats/explainer.json` (25-45 s) is the
default of the explainer and law programs; `formats/number.json` (20-25 s) is the rubric „დღის ციფრი“'s and
`formats/digest.json` (45-60 s, `chapters: auto`) the morning digest's (`veasy:rubrics`) (a program names its format: `veasy:programs`). `auto` and `family` follow the story's brand pack
(`options --brand <name>` shows its table). tbilisi.today: hard news `editorial` + `anchor`, light news `kinetic`,
service news `cards`; people's news `warm`, numbers and tech `clear`, sports `plain`. SiTech: its own `sitech`
voice (Charon) for every family. A format works for every brand; a pack's own voice only for that pack.

## Themes: the same pack on another ground

A pack may have several palettes (brand.json `themes`, `veasy:brands`): both shipped packs have `dark` (the
default) and `light` (paper). `options --brand <name>` → `themes` lists a pack's, with `allowed`. A theme changes
only colors (and a logo drawn for that ground), never the layout, the motion or the rules.
- `"theme": "auto"` lets variety alternate a pack's allowed themes evenly (a re-render keeps its own); a
  director may prefer some by name (`draw` prefers `light`, a drawing on paper).
- `allowed: false` is a theme the owner has not approved yet (tbilisi.today's `light`: its brand v1.2 is dark).
  `auto` never picks it, and `render` and the queue refuse it; `plan`, `probe`, `still` and `selftest` take
  `--theme light` to preview it.
- Per render: `--theme light` on `render`, `still`, `plan`, `probe` and `queue add`.

## Variety comes on its own

Inside a format, every video gets its own hook layout (stack, lead, blocks, underline), background motif (grid,
diagonal, dots, rules, plain, and `icons`: the story's main icon tiled faintly, only for a story that has one and
never for crime or deaths), entrance (rise, slide, reveal, scale), transition (when `auto`; `meter` in editorial and
kinetic) and music loop
(four per family): the least used lately for the brand (`options` → `variety`). So a format doesn't need to vary
these by hand; fix one in a format only when a show must always look one way (e.g. `"transition": "cut"`).
Each story's **director** (`veasy:directors`) narrows these choices and sets the motion and its direction. A
director is not a format key: it comes with the story, or from `--director`.

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

The palette itself, the logo and words (the brand pack's, `veasy:brands`; a format only picks one of the pack's
themes), the safe zone, the news rules, the
date/sources/link from the data, and the voices' approval: a new voice preset or a new look is code or a pack
(`voices.py`, a pack's `voices`, `remotion/src`) and needs the owner's ear or eye first.
