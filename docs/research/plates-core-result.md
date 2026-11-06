# Plates Core Result

## 1. "Done When" Evidence Matrix

| "Done When" Requirement | Status | Evidence (File, Command Output, Still) |
|---|---|---|
| `engine plate example --seconds 4` gives a tone-mapped clip in both packs, and a second call answers from the cache in under a second. | In Progress | Unit 1 done: `plates.make` bakes, tones all 4 pack/theme lines, answers from cache (`tests/test_plates.py` Baked). CLI wiring pending. |
| One Remotion film and one composed film show a plate behind real facts: rendered, `qa` and flash pass, `probe` passes, and the critic has judged the frames. | In Progress | Pending Item 5 & 6 & 9 implementation. |
| Tests prove the refusals, the tone line, the cache and the ledger. | In Progress | Tone line, refusals (library level), cache, ledger entry proven in `tests/test_plates.py` (16 tests pass). Refusals at brush/check and ledger validation pending. |
| The skill states what reading a plate costs in each engine, as measured. | In Progress | Pending Item 8 implementation (`skills/plates/SKILL.md`). |
| All gates pass (`python -m unittest discover -s tests`, `tsc --noEmit`, `engine selftest`). | Ready | Baseline passes (773 tests, 0 errors, tsc clean). |

---

## 2. Commit List

0. `5c8647a` wip: state left by the Antigravity run (unverified, then verified: bakes)
1. `(pending)` `docs(research): research 16 sources on broadcast plates, tone mapping, banding and headless video seeking`

---

## 3. What Was Not Done & Why

*(Will be updated as backlog items progress)*

---

## 4. Owner Decisions

*(Any items requiring owner confirmation)*

---

## 5. Shared Files Touched

| File | Nature of Touch | Justification |
|---|---|---|
| `docs/research/plates-core.md` | New | Comprehensive research report and backlog |
| `docs/research/plates-core-result.md` | New | Result evidence tracker |

## 6. Measurements (this run, 2026-11-07)

- Tone: the lookup stage puts every pixel within 0.72 of the canvas-to-ink line (limit sqrt(3)/2 = 0.866) and uses at
  most 256 colours, for all four lines (both packs, both themes). A decoded x264 crf 14 clip adds codec noise: mean
  distance 1.0-1.2, p99.9 3-5, max 12-16 (x264 ringing at edges; crf 0 gives max 2.4 but 6x the size). The research's
  claim of "zero off-palette colours" holds for the toned frame, not for the compressed clip: stated plainly.
- Cache hit: `plates.make` second call 1.5 s the first time it was timed including interpreter and brand loading; the test
  holds the call itself under 1 s (node `--hash` about 0.1 s).
- Bake: about 200 ms a frame at half scale on this machine; the browser start costs most of a one-second bake.
- run.mjs: `--hash` added (print the content hash, no bake); the hash used the spec's file path, now its contents.
