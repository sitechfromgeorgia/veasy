# Thread object: research

**The line:** `python -m tt_shorts.engine render stories/veasy-thread.json --voice silent` gives a film whose object
(from the story's chosen idea) sits in at least 3 scenes, travels across the cuts and changes state.
`python -m tt_shorts.engine thread <story>` shows the same plan for free: drawing, state, which scenes carry it, seats.

## What the build needs

| Question | Answer | Source |
|---|---|---|
| Morph in Remotion | `interpolatePath(t, a, b)` from `@remotion/paths`, MIT, version pinned to `remotion`. A port of d3-interpolate-path: paths of different lengths are matched, no resampling on our side | https://www.remotion.dev/docs/paths/interpolate-path |
| Morph in HyperFrames | `flubber` (MIT), through the pinned script list in `tt_shorts/compose.py` | https://github.com/veltman/flubber |
| What makes a match cut read | The same form at the same place across the cut: position and silhouette carry it, not the colour | Bordwell/Thompson, *Film Art* (graphic match); `reports/...` § ეტაპი 3 |
| What an object wipe needs | The object crosses the frame, its body hides the swap | `concepts/devices.json` `object-wipe` |
| The cut stays quiet | Continuity hides a cut, it needs no sound of its own | Smith 2017, in `reports/...` § ეტაპი 3 |

## What the code already gives

- `concept.py`: `object`, `verb`, `device` are on the story, code-owned. `verb` is free English: a table maps it to a state.
- `drawings.py`: `candidates(motif)`, seeds and saved drawings. `art.py`: a safe tree (`art.sanitize`), tokens only.
- `variety.py`: `NEEDS_ICON` is the pattern for an option only some stories may have. `TRANSITIONS` stays untouched:
  the new cuts are added only for a film with a thread, so no news video can draw one.
- `captions.py` is the rule for geometry: laid out in Python, never measured in the render tabs. Seats follow it.
- `goal/plates-core`: a type outside `news_check.SCENE_TYPES` is refused by N1 (`MADE_PICTURE_TYPES`). Same way here.

## Decisions

1. **Seats are computed in Python** (`thread.seats`): a rectangle per scene, from the scene's type and text load. The
   scene is told to keep that room free (`Frame`, `reserve`), a layer above the scenes draws the object. No DOM
   measuring, so a frame is a pure function of its number, and the probe can check text against the seat.
2. **One layer, not a copy per scene:** the object glides from seat to seat across a cut in every thread film, whatever
   the transition. `match` and `object` are two more ways through that same window.
3. **States work on any drawing:** a silhouette traced in Python from the line art (`thread.outline`), then `drain`,
   `fill`, `break`, `grow`, `shrink` on it. No per-drawing authoring, so a writer's checked drawing works too.
4. **An unknown verb gets no state:** the picture must not assert what the idea didn't say. It warns.
5. **Never for news, crime, incidents, deaths:** no concept step there, `thread.plan` refuses, `state` is outside N1's
   list and `match`/`object` exist only with a thread.

## Licences

| Package | Licence | Use |
|---|---|---|
| `@remotion/paths` 4.0.539 | MIT | morph in Remotion |
| `flubber` | MIT | morph in HyperFrames, if cheap |

## Backlog, most valuable first

1. Object across scenes (value high, effort medium). 2. `state` brush (high, medium). 3. `match` (medium, medium).
4. `object` (medium, small). 5. HyperFrames blocks (medium, unknown). 6. Ten blind pairs (high, medium).
