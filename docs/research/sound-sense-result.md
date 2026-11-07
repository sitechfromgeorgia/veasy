# sound-sense result

Branch `claude/sound-sense-05367d`. Lane: the sound part of phase 3. Nothing pushed or merged.

## What shipped
- `sfx: meaning` (in `sfx.OPTIONS`, `formats.SFX`, `engine options`, `veasy:formats`, README, `veasy:media`). One
  `impact` on the main moment plus `small_count` (2-4, three in 30 s) small sounds: the object's own sound, a pop on a
  mark, the outro chip, a chart's first bar, the hook opening. No sound on a transition (`NEAR_CUT` 0.12 s from any cut;
  a word or the moment sitting on a cut is moved 0.12 s into it). Cues come from the timeline and the code-owned
  `story["concept"]` only. `sfx` stays `off` by default.
- The main moment (`sfx.moment`, by code): the big number settling, else the narration saying the idea's object, else the
  hook's mark, else 45 % of the film; kept 1.0 s from the start and 1.5 s from the end. Written to `props["sfxMoment"]`.
- The object's sound (`sfx.object_sound`): six synthesized sounds in `tools/compose_sfx.py` (wood, glass, metal, paper,
  water, soft), chosen by the object's last word's stem, else a hash of it. No samples. `impact` is a seventh new sound.
- Music (`tt_shorts/music_hits.py`, `props.mix_audio`): the hits are the composer's own data (bar openings, kicks); the
  loop start is `(-moment) mod bar`, applied as `atrim=start=` on the looped stream (not `-ss`: that would restart every
  later loop at the offset). Level untouched.
- Composed (HyperFrames) films: `sfx: meaning` there gives beat-named sounds only, no whoosh on wipes; no music offset
  (they have no moment yet). See Owner decisions.

## Done when
- Count of sounds, none on transitions, one constant level: `tests/test_sfx.py::Meaning` (three 30 s stories: one
  impact + 3 small each; no cut sound names and none within 0.12 s of a cut for four stories and four transitions; the
  mix graph has one static `volume=-6.0dB` for the effects, no sidechain, no envelope). Passing.
- Hit within tolerance on three stories: `tests/test_music_hits.py` mixes a real composed loop through `mix_audio` and
  finds where the film's audio sits in the loop by cross-correlation. Measured (tolerance stated: 60 ms):
  number moment 6.200 s -> hit at 6.205 s; idea 13.370 -> 13.375; hook 2.767 -> 2.772 (5 ms: the aac priming). Passing.
- `ebur128` on a mixed film (bed only, 30 s, politics-1): integrated -17.1 LUFS without the offset, -17.1 LUFS with it
  (moment 13.37 s, offset 1.949 s). The test allows 0.3 LU. Passing.
- Nobody has listened. I can't hear. All sounds are formulas; the check is arithmetic and waveform measurement only.
- Full suite: 784 tests, 2 skipped. First run: 6 failures, all "probe error: Node.js" because `npm ci` had not been run in `compose/` and `remotion/`. After `npm ci`, those six test groups (29 tests) pass. No full re-run after that: the other 778 passed in the first run, which had every code change.
- `tsc` and `selftest`: not run, no Remotion or scene code touched.

## What the owner should listen for
1. `impact`: heavy enough on a phone speaker (it has no sub; the harmonics carry it), not boomy, not a thud copy.
2. Does the music's bar opening land with the main sound as one event, or sound like a flam? (the aac start is ~5 ms late.)
3. The six object sounds: does a key/bottle/box/paper/water/cloth read as that thing? Is any irritating on repeat?
4. Does the loop starting up to one bar (2-3 s) in, with the usual fade-in, sound natural?
5. Is the film quieter and more intentional than `sfx: on`, or too bare?

## Owner decisions
- The main moment order (number > idea > hook > 45 %) is my choice; say if the idea's turn should outrank the number.
- The object's word is the only trigger for the idea's turn; there is no "turn" field in `concept` yet.
- Composed films need a moment and cue timing of their own (a film's timing `t`); not built.
- Material table (`sfx.MATERIALS`) covers ~50 Georgian stems; other objects get a hash. Extending it is a data task.
- Decision 10 (a voice pause before the peak, stop-time) left alone, as briefed.
