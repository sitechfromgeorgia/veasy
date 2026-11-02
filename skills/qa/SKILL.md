---
name: qa
description: "Use after rendering a Veasy video (a tbilisi.today or SiTech Short, any brand) and before it is shown or published, to verify length, size, loudness, captions, voice and facts. Examples: \"check this video\", \"is 24886 ready to post\", \"the captions look wrong in this render\""
---

# QA a rendered video

1. Machine checks:
   `python -m tt_shorts.engine qa <file>.mp4 --format <format>`. `problems` must be empty: 1080x1920, length
   inside the format's window, loudness -19..-13 LUFS (voice at -16 with the music ~13 LU under it). It also writes
   `<file>.sheet.jpg`, eight frames across the video: look at it.
2. The story check must have passed: `python -m tt_shorts.engine check <story.json> --sources <story>.sources.json`.
   A queue job in state `done` passed both; `held` means it rendered but QA found problems (its `error` says which).
3. Look (the sheet, or `engine still` for exact scenes):
   - nothing clipped or overflowing; story text above the captions; nothing right of x=940 below y=1100;
   - the date, the outlets line and the pack's link visible (tbilisi.today/stories/<id>, sitech.ge/ka/blog); the
     pack's footer line bottom right; QR on the end card; the pack's logo and colors, not another client's;
   - the accent (tbilisi.today red, SiTech orange) only on dots, the progress head, the spoken word's underline
     and the CTA button, never as text color.
4. Captions: they are laid out once by `tt_shorts/captions.py` and must not jump. `page` pages stay ≥ 1 s and the
   box never moves; `roll` scrolls smoothly. If something looks unstable, re-run `python -m unittest
   tests.test_captions` and report the frame numbers instead of hand-tuning the render.
5. Listen once, start to end: names said right (add a `say` entry or a `lexicon_ka.json` entry), no skipped words
   (the render's JSON lists `voice_qa`: words the aligner barely heard, the likely ones), music steady under the voice, no clipping.
6. Facts: the hook matches the articles; numbers, names and quotes match; nothing is the writer's opinion.

If any step fails, fix the story or the inputs and render again (the voice is cached unless the narration changed).
Never publish a render made with `--engine edge` or `silent`.
