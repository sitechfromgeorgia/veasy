# sound-sense: research (only what the build needs)

One line for the user: `--sfx meaning` (or `"sfx": "meaning"` in a format). They get one main sound on the film's
main moment, 2-4 small ones, the object's own sound, and the music loop shifted so a heavy hit lands on that moment.

## What the build rests on
- Sound follows meaning, not mechanics (Chion, "synchresis": a sound fused to an image makes it read as one event;
  https://sonicfield.org/wiki/audio-vision). So few sounds, each on something the story says or shows [?].
- A cut needs no sound of its own when the narration is continuous: the voice already hides it
  (Smith 2017, https://eprints.bbk.ac.uk/14904/). So `meaning` puts nothing on a transition [?].
- Veasy's own rules (CLAUDE.md, owner's ear): one constant level, no ducking, no risers, no build-ups, cues from the
  timeline, never from the writer, `sfx` off by default. Decision 10 (a voice pause before the peak, stop-time) is the
  owner's: not built here.

## Findings from the code
- The music loops are `tools/compose_music.py`'s: one family, 4 variants, whole bars at a known tempo. Soft kicks sit
  on known beats (`kick`), and every bar starts with a bass note, so the hit times are the composer's own data:
  kicks, else bar downbeats. No onset detection and no new dependency needed. The m4a files are not in git.
- A loop starting at offset `o` puts the loop's time `h` at film time `h - o` (mod loop length). `-ss` on a
  `-stream_loop` input makes every later loop restart at `o` (a seam), so the offset is applied in the filter graph:
  `atrim=start=o` on the already-looped, infinite stream.
- Level: the loops are flattened bar by bar (spread under 1 dB), so a different start does not change the bed's
  level; checked with ffmpeg `ebur128` on a mixed film (see the result file).
- The aac encoder adds ~21 ms of priming: well inside the stated tolerance (60 ms).
- Props already carry what finds the main moment: scene `from`/`duration`, `mark.at`, `type`, `words` (seconds).
  The idea (`story["concept"]`: object, device) is code-owned; the object's word is found in `words` by its stem
  (`concept.root`).

## Not verified
- Nobody has listened to any of it. The sounds are synthesized by formula; their taste is the owner's ear.
