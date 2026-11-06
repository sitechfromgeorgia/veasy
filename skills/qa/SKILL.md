---
name: qa
description: "Use after rendering a Veasy video (a tbilisi.today or SiTech Short, any brand) and before it is shown or published, to verify length, size, loudness, layout (the probe), captions, voice and facts; also before merging a change to how videos look (selftest). Examples: \"check this video\", \"is 24886 ready to post\", \"the captions look wrong in this render\", \"did my scene change break a look\""
---

# QA a rendered video

Videos go out without a person looking, so the engine checks itself first. Your job: read its findings, look where
it points, and never publish a video with problems.

1. Machine checks:
   `python -m tt_shorts.engine qa <file>.mp4 --format <format>` (tool `veasy_qa`). `problems` must be empty:
   1080x1920, length inside the format's window, loudness -19..-13 LUFS (voice at -16 with the music ~13 LU under
   it), the hook on screen at frame 0 (`opening_ink`: the share of ink in the hook band y 250-1100 of the very
   first frame, at least 2%; a swipe decides there), the layout probe's problems from the render (`probe`) and
   `flash`: no more than 3 flashes in any second over a quarter of the screen (ITU BT.1702, `tt_shorts/flash.py`; a
   safety hold, whichever engine drew the video: slow the cuts or inversions it names).
   It also writes `<file>.sheet.jpg`, eight frames across the video: look at it.
   A composed film has more to see, for free: `engine compose look <story>` (`veasy:compose`).
2. The story check must have passed: `python -m tt_shorts.engine check <story.json> --sources <story>.sources.json`.
   A queue job in state `done` passed both; `held` means it rendered but a check found problems (its `error` says
   which: a `probe ...` line is a layout problem).
3. The layout probe (`tt_shorts/probe.py`, tool `veasy_probe`): every render measures where each text block
   really is, at each scene's settled frame, in the browser that draws it. Run it alone, free, before a render:
   `python -m tt_shorts.engine probe <story.json> --look all [--stills <dir>]`. Each problem names the rule, the
   scene and frame, the text and the numbers:
   - `band`: scene text outside the scene band (y 248-1380): too many or too long lines;
   - `rail`: text right of x=940 below y=1100, under the platform's like/share buttons;
   - `captions`: caption text below y=1552; `frame`: text outside the 1080x1920 frame;
   - `overflow`: text past its box (a line wider than its card, a label cut off, a sub line on the card's footer);
   - `glyph`: a character the brand font lacks (it would show as tofu or another font; FiraGO has no ₾: write
     ლარი); `font`: not the brand font, or a frame laid out before the font loaded;
   - `size`: text shrunk under the minimum (24 px in a scene, 40 in captions).
   Fix the story when its text is too long (shorter lines, labels, names); when the story is fine and a scene
   component draws it wrong, that is an engine bug: report the scene type, look and frame. Look with `--stills`.
4. Look (the sheet, or `engine still` for exact scenes) for what code can't judge: the pack's logo and colors, not
   another client's; the accent (tbilisi.today red, SiTech orange) only on dots, the progress head, the spoken
   word's underline and the CTA button, never as text color; the date, the outlets line, the pack's link and
   footer line visible; QR on the end card (`outro` card) or on the chip over the last scene (`overlay`, `loop`:
   left of x=940, above the captions); `loop`: the last frame is the first one (`engine still --frames
   0,<last>` shows both); a drawing that shows the story.
5. Captions: they are laid out once by `tt_shorts/captions.py` and must not jump. `page` pages stay ≥ 1 s and the
   box never moves; `roll` scrolls smoothly. If something looks unstable, re-run `python -m unittest
   tests.test_captions` and report the frame numbers instead of hand-tuning the render.
6. Motion (`tt_shorts/motion_rules.py`, in the render's JSON as `motion` and in `veasy_plan`): `motion read` is a
   text on screen too briefly to read (0.5 s + 0.3 s a word) and holds the video like a probe problem; give its
   scene more narration or shorten the text. The others are warnings: `still` (over 3 s with nothing new),
   `kinds` (over 3 transition kinds), `pingpong` (cuts A-B-A, or back and forth), `repeat` (one type twice).
7. Listen once, start to end: names said right (add a `say` entry or a `lexicon_ka.json` entry), no skipped words
   (the render's JSON lists `voice_qa`: words the aligner barely heard, the likely ones), music steady under the
   voice, no clipping.
8. Facts: the hook matches the articles; numbers, names and quotes match; nothing is the writer's opinion.

If any step fails, fix the story or the inputs and render again (the voice is cached unless the narration changed).
Never publish a render made with `--engine edge` or `silent`.

## What keeps failing

`python -m tt_shorts.engine learn [--brand tbilisi-today] [--days 7]` lists the rules failing most lately (the
`failures` table in `veasy.db`: the writer's failed passes, checks, render and QA problems, errors by class). The
writer reads the same list for its brand before it writes (`writer_block`), so a frequent mistake becomes rarer.
A rule that keeps failing on layout points at a scene that needs a fix in code, not one more retry.

## Before merging a visual change (scenes, looks, captions, brand.ts)

`python -m tt_shorts.engine selftest` renders the fixtures (`stories/veasy-scenes.json`, `stories/veasy-demo.json`)
in every look with one fixed style, probes them, and compares each scene's still with `tests/golden/`. It reports
which scenes changed and where the stills are: look at them. A change you meant: `selftest --update` and commit the
goldens with it. One you didn't: fix it. Any probe problem fails the selftest too. About half a minute; it is not
part of the unit tests.


## Pre-flight Visual Critique & Dry Run (before rendering)

Before rendering or paying for a voice, run:
1. `python -m tt_shorts.engine dry-run <story.json>` (tool `veasy_dry_run`):
   Free calculation ($0.00) of character counts, spoken seconds, estimated TTS cost, monthly budget status, and whether the voice/bundle is cached.
2. `python -m tt_shorts.engine critique <story.json>` (tool `veasy_critique`):
   Runs an automated pre-flight visual checklist over the plan's stills: safe zones, text reading load, static stretches, novelty, hook pacing, and brand contrast. Returns score (0-100), grade (PASS / NEEDS_ATTENTION / FAIL), and contact sheet path (`.plan.jpg`).
