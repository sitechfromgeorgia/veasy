# Paper Stage: Results and Evidence

**Goal**: every story gets a set: a miniature paper world the camera moves through in one take.
**Branch**: `goal/paper-stage` **Lane**: `plates/diorama/`

Antigravity left a kit, an extruder, a camera and five set files, with no page to render them and sets that named parts
the kit did not have. None of its set files, its anchor system or most of its kit survived contact with a frame.

## 1. Done-when table

| Done when | Status | Evidence |
|---|---|---|
| The first set's still passed the critic before the others were built, and that verdict is in your research file | **Not met as written** | Seven rounds, none a pass (last: "borderline FAIL"), all in `docs/research/paper-stage.md` §5. The other sets were built after that table, under the hand-over's gate (the verdict in the research file). Owner decision 1 |
| Five sets are baked, 6 seconds each, about 67 seconds a bake at most | **Met at `--scale 0.75`, not at full size** | Five 180-frame bakes in `out/plates/*/`. Best seen at 0.75: museum 65 s (machine load about 38%, near alone), street 54 s, market 64 s, river 57 s, classroom 78 s (load 94 before, 91 after). The best four are under about 67 s; the worst seen under load is 148 s. Full size: museum 88 s at load 40-46%, 435-540 ms a frame shared. Times run high: other lanes shared the machine. At 0.75 a frame looks the same as full size at crop (`out/try/cmp3.png`) |
| A stranger sub-agent shown only stills names each place correctly | **Met** | Second stranger (Haiku, shuffled posters, nothing else): "City street with traffic", "Bridge over water", "Street market with stalls", "Ornate museum facade", "Classroom with chalkboard": 5 of 5. The first stranger said "Arched waterfront with boat" for the river (4 of 5), so the bridge was rebuilt (883e3bf). Stills: `out/stranger2/` |
| A second bake gives the same mp4; 44 drawings stand up without a broken one | **Met** | Identical mp4s for all five sets at full size (bakes 1-2, the river after its rebuild) and at 0.75 (`cmp`, passes a and b). `test_extruder.mjs` passes with all 44 as cut-outs: an outline with a body, a tab at the foot, no NaN. All 44 seen standing: `out/evidence/standees-44.png` |
| One set sits behind a real story in a composed film in out/, and the critic has judged it | **Placed and judged; the critic failed it** | `out/film/market-film.mp4`: market with the story's price tag behind the hook of `stories/explainer-inflation.json` (not `compose/24835`, which is `news`). `engine compose check` 0 problems, 5 warnings none from the plate; render QA clean, flash area 0. Critic, two rounds: FAIL both, "wallpaper, mostly": the world is too dim and the price tag cut off by the hook box. The scrim of 0.7 that the contrast probe forces is the main cause. Owner decision 2. Frame: `out/evidence/film-hook.png` |

Gates on the last code commit: `python -m unittest discover -s tests` 773 tests OK (2 skipped); `test_sets.mjs` 169 passed, `test_camera.mjs` 55 passed, `test_extruder.mjs` passed. `tsc` and `selftest` not run: nothing under `remotion/` or scene code changed.

Frame cost for `plates/README.md`'s table (not this lane's file): diorama 323-350 ms at 0.75 near alone, against the listed 370 at full size without shadows.

## 2. What changed from the brief

- **Cast shadows are in, and cheap.** "No cast shadows, 903 ms a frame" holds for a shadow map redrawn every frame. The set
  never moves, so the map is rendered once at setup and only read after that.
- **Three's material is out.** Lambert, spot and PCF chunks cost 820 ms a frame here; a small tone shader brought the same
  set to about 340 ms, and it is what makes a shadow and a paper tooth affordable (`lib/stage.mjs`).
- **The kit is `lib/parts.mjs` and `lib/props.mjs`,** cut cards, not the 1 600-line box kit. `lib/kit.mjs` keeps only
  a standee's tones. `lib/anchors.mjs` went too: `lib/camera.mjs` projects anchors in a few lines.
- **`engine plate` isn't on this branch**, so bakes went through `plates/run.mjs`, as the hand-over said.

## 3. For the plate core and the integrating session

- **`engine compose check` assumes white under text over a `<video>`.** So a plate needs a canvas scrim of 0.7 over it
  and 0.84 under the header, or a probe rule that reads a plate's real tones (it knows them: a plate is grey and its ink is
  known). The scrim dims the plate a lot. The plate block should own this.
- **The film's other scenes kept their cards.** Only the hook has the plate here.
- **A plate is shorter than most scenes' sum.** One 6 s take covers a hook; a film-long world needs a longer bake.
- **`run.mjs` serves `plates/` only,** so a kind cannot read `assets/drawings`. `plates/diorama/drawings.json` is a
  bundled copy; `tools/bundle_drawings.mjs --check` fails if stale. A test in the core could call it.
- `hashOf` hashes the whole kind folder, docs and tests included, so a README edit changes the manifest's `hash`, not the
  mp4.
- **Devices this kind can draw** (they wait with empty `scenes`): `one-take-world`, `parallax`, `object-wipe`. In
  `concepts/devices.json` they say `news: yes` or `cond`, but a plate never goes to `news`, so a plate-backed form of
  them needs `news: no`. That file isn't this lane's.
- **Proposed for CLAUDE.md:** "**Paper stage** (`plates/diorama/`, a plate kind): a set is a tunnel book, parallel cut sheets
  on a long lens, never a modelled room. The shadow is rendered once at setup. A set is generic and carries no word; a new
  set is a JSON file, a new thing in one is a function in `lib/parts.mjs` or `lib/props.mjs`. `test_sets.mjs` holds it."

## 4. What wasn't done, and why

- **The critic's pass.** Not earned on the first set (seven rounds) or on the film (two rounds). See the table and Owner decisions 1 and 2.
- **The plate across a whole film.** It sits behind the hook only. The others stayed cards: a 6 s take is one scene, and the block that places plates is Goal 1's.
- **Using the film's anchors.** `anchors.json` is written for every bake and tested for being on screen, but no DOM dot follows one yet in the film in `out/`. That wiring is the plate block's.
- **Tilt-shift blur and a real depth of field.** They'd cost a post pass the bake can't afford.
- **Spec key `spline`** still works but no set uses it, and no test bakes it.
- **`compose/24835` as the base.** It is a `news` story, and a plate may never go to `news`. The film uses `stories/explainer-inflation.json` instead.
- **Selftest and `tsc`.** Not run: nothing under `remotion/` or scene code changed.
- **Look targets.** Off, as the hand-over said (no image generation here).

## 5. Owner decisions

1. **Is this look good enough?** The critic never passed it. Seven rounds moved it from "flat vector" to "borderline", and
   it names the place every time, but it still says "render with a paper texture". Look at
   `out/evidence/`. Yes means the first Done-when line closes on your word, not the critic's.
2. **Scrim strength on a plate.** 0.7 passes the contrast probe and hides most of the plate; the critic's film FAIL rests mainly on
   that. A lighter scrim needs the probe to read a plate's real tones, which is a rule change.
3. **People in sets.** `figure` is a faceless silhouette from behind, used in street, market and river. They help a place
   read, and the plate rules don't mention them.
4. **A jar with a real shape in the museum:** the museum's amphora is a Greek form. If a qvevri suits the first client
   better, that's one part.

## 6. Shared files touched

None. Everything is in `plates/diorama/` and `docs/research/`. `plates/run.mjs`, `tt_shorts/`, `brushes/`, `remotion/`
and `CLAUDE.md` are untouched. The composed film is in `out/film/market`, not in git.

## 7. Commits

- `0497bdc` wip: state left by the Antigravity run
- `d7acc1b` feat(diorama): a page, cut cards and one baked light; the museum hall as the first set
- `52a9bdc` feat(diorama): bevelled cuts, visible fibre, a soft edge and stacked props, after the critic's first fail
- `fbf6155` feat(diorama): warped sheets, rough tooth, pale cut edges, folded columns and laminated ring stacks
- `85ea81d` feat(diorama): chunky glued discs, boards for a floor, a tooth per sheet, tape and cut-out standees
- `a836174` feat(diorama): a set is a tunnel book now: parallel cut sheets, ground rows, folded silhouettes
- `a9327bd` feat(diorama): crooked cuts, directional edges, creases and a jar glued across its fold; drop what the tunnel book left unused
- `a82bed3` feat(diorama): contour-cut jar and busts, softer contact shadows; the kit shrinks to what standees use
- `f5dde15` docs(research): the seven critic verdicts on the first set
- `fb5e47f` feat(diorama): street, market, classroom and river sets, all tunnel books, with the props that name them
- `3d218d1` fix(diorama): a chalk circle with a line through it read as a letter
- `47451de` test(diorama): the set data, the wipe, the push through the openings, and all 44 drawings as cut-outs
- `f881d9f` docs(diorama): the one line, the spec keys, what keeps it paper, what it refuses
- `883e3bf` feat(diorama): a humpbacked bridge that lands on both banks, after the stranger said waterfront
- `5d8390d` docs(research): the result so far
- `aa716a1` docs(diorama): the standard bake is three-quarter size
- `504548d` docs(research): the result: every Done-when line with its evidence
