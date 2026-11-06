# Plates Core Result

## 1. "Done When" Evidence Matrix

| "Done When" Requirement | Status | Evidence (File, Command Output, Still) |
|---|---|---|
| `engine plate example --seconds 4` gives a tone-mapped clip in both packs, and a second call answers from the cache in under a second. | In Progress | Pending Item 1 & 3 implementation. |
| One Remotion film and one composed film show a plate behind real facts: rendered, `qa` and flash pass, `probe` passes, and the critic has judged the frames. | In Progress | Pending Item 5 & 6 & 9 implementation. |
| Tests prove the refusals, the tone line, the cache and the ledger. | In Progress | Pending Item 2 implementation (`tests/test_plates.py`). |
| The skill states what reading a plate costs in each engine, as measured. | In Progress | Pending Item 8 implementation (`skills/plates/SKILL.md`). |
| All gates pass (`python -m unittest discover -s tests`, `tsc --noEmit`, `engine selftest`). | Ready | Baseline passes (773 tests, 0 errors, tsc clean). |

---

## 2. Commit List

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
