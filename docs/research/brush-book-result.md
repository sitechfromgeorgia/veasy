# Brush book: result

Lane `goal/brush-book`, worktree `D:\MyStaff\Veasy-brush-book`. Antigravity ran out of quota after the research;
Claude Code built everything below. Rebase onto main is left to the integrating session.

One line for the user: `python -m tt_shorts.engine gallery --find "a number"` gives the best entries as JSON (id, kind,
real still, command, when not to use); `gallery --real` renders and writes `out/gallery/index.html`.

## Done when

| # | Line | Status | Evidence |
|---|---|---|---|
| 1 | A test finds a real file for every brush x look x theme and every other listed item | done on this machine | `engine gallery --real` made 269 files, 0 problems (31 brushes x 3 looks x 2 themes = 186 stills, 8 hooks, 10 motifs, 8 entrance strips, 14 transition strips, 8 directors, 18 styles, 5 rubrics, 9 composed blocks, 3 templates); a second run took 1.4 s, all 269 cached. `tests/test_gallery.py::RealFiles` checks every promised file is a real image (skips where `out/gallery` is not rendered: `out/` is not in git). Plates: listed only when `plates/*/poster.png` exists (none on this branch). |
| 2 | The page opens and search works at phone and desktop width | done | Served over http (port 31080) and driven in the built-in browser at 390 px and 1280 px: no horizontal scroll, 1 column on the phone and 3 on desktop, images load, filters and the light/dark switch work. Queries "a number", "a place", "a quote", "compare two things", "a ranking", "percent of a whole" put the right brush first; "a process" puts `steps` first; nonsense shows "0 shown" and the empty message. |
| 3 | A sub-agent given a story and only this page picks a sensible look in under 3 tries, for 5 stories | done, 4 clear and 1 arguable | A Haiku agent given only the skill and `gallery --find` (not the code) picked, in 1 try each: water cut -> `sign` (arguable: `stat` for 3200 households is the more natural pick; it named stat as runner-up), exact quote -> `quote`, five ranked resorts -> `ranking`, quake region -> `where`, passport renewal -> `steps`. 5 of 5 within 3 tries. |
| 4 | 12 examples and 6 pairs exist and pass `check` | done | `examples/index.json`; `tests/test_gallery.py::Examples` runs `engine.check_story` on all 12 films (must be empty) and on every pair (bad fails with the line named in `check_says`, fixed is empty). |

The cold user got `--find` and the skill, not the HTML page itself (an agent cannot run the page's script); the page and
`--find` share the same words and need-scores (`gallery.SYNONYMS`, `need_score`).

Gates: the full unit suite was run once on the last commit (result line below); `tsc` and `selftest` were not run
because no Remotion or scene code was touched (only Python, JSON, docs and a skill).

Full suite on d397cff: `python -m unittest discover -s tests`: Ran 786 tests, OK (skipped=2).

## What was built

- `tt_shorts/gallery.py` (replaces the SVG-card generator): `items()` reads brushes, variety options, directors, styles,
  rubrics and plate posters from data, so what merges later appears after the next `gallery --real`. `render()` draws real
  stills through the engine's own probe pipeline (silent, no voice, no network), cached by a hash of the item's data, the
  default pack, Remotion's source and props.py. Entrances and transitions are 5-frame strips (no mp4 clips: see below).
  `manifest.json` records, per brush still, the exact `engine still ... --frames N` command and the story it came from.
- `engine gallery [--real] [--find Q] [--examples --seed S] [--only KIND] [--limit N]`.
- `out/gallery/index.html`: one file, no network: search by need, a filter per kind, a light/dark switch, every brush in
  every look and theme, copyable commands, "use when" and "not when".
- `examples/`: 12 annotated films (news x7 incl. 4 directors' tellings of one story, digest, explainer, law, story,
  rubric; two packs) and 6 bad-to-fixed pairs, with `index.json` (asked, shape, turned_down, learn). `gallery --examples
  --seed S` rotates them.
- Skill `veasy:brush-book` (6 KB), tool `veasy_brush_book`, link `.claude/skills/brush-book`.

## Commits

1. `f1080f1` research (Antigravity).
2. `c0fc753` the harness, page, examples, skill, plugin entry.
3. `d397cff` in-page search ranking fix, result file; `a93cb60` full-suite result.
4. the last commit of the branch (`git log -1`): blocks and templates, the added-later test, this update.

## Added after the first hand-over (second pass)

- **Composed blocks (9) and templates (3)** are in the book, read from `compose/blocks/` and `templates/`: `compose.blocks()`
  and `compose.templates()`. Each picture is a real HyperFrames frame strip: a throwaway project is scaffolded in
  `out/gallery/projects/<id>` (a block from `--blocks`, a template from the finished film it was promoted from, or
  scaffolded with its beats anchored on the story's narration when that film is not in the repo), its slots are
  filled with their own examples, `compose look` takes the free sheet, and three frames are kept side by side. About
  20 to 30 s an item, cached by a hash of the item's own files. Commands: `compose scaffold <story> --blocks <id>` or
  `--template <id>`. Looked at: `block-chapter-card`, `template-fable-story`.
- **Added later, no code change** (`tests/test_gallery.py::AddedLater`): a throwaway brush, block, template, plate
  poster and variety option each appear in `items()`, on the page and in `--find` with no edit to `gallery.py`, and are
  gone again afterwards. A new process is what a rebuild is: the engine caches brushes per process, so the test clears
  that cache.
- **Why not mp4 clips.** An entrance or a transition is a few frames long and the thing a reader needs is how it moves
  and settles: five frames side by side show that at a glance, load instantly, cost about a second each instead of a
  video render, and an agent can read them (it cannot watch an mp4). A clip would add about 40 full renders, megabytes
  per item and nothing a strip does not already say. If the owner wants loops for the human page they can be added
  under a `--clips` flag without touching the catalogue.

An observation for the blocks' owner (not fixed here, outside this lane): the `number-reveal` block's number shows as a
row of dots in the `compose look` frames, not as the digits of its `value` slot.

## Not done, and why

- Short mp4 clips: see above, a deliberate choice.
- Plates: no poster exists on this branch, so none is listed. When another lane bakes `plates/<kind>/poster.png`, it
  appears on the next rebuild (test: `test_plate_posters_are_read_from_disk_when_they_exist`).
- The HyperFrames-engine styles are drawn through Remotion with the style's own picks (the card says so); they are not
  that engine's compose of the style.
- Text on the stills is the brush's example plus a placeholder sentence in the captions: it claims nothing.
- Not covered by the cold-user test: blocks and templates (it ran before they were added).

## Owner decisions

1. Clips: do you want real mp4 loops per transition/entrance (machine time, about 40 renders) or are the strips enough?
2. Should `out/gallery/` stay out of git (as now, about 17 MB of JPEGs, goldens-like per machine) or ship in the repo so the
   page opens on a fresh checkout?
3. The stills use the default pack's two themes (dark, and the pack's light preview). Show SiTech's themes too?

## Shared files touched (all additive)

- `tt_shorts/engine.py`: the `gallery` subcommand's flags and handler; `options` no longer overrides a style's `still` path.
- `tt_shorts/styles.py`: `summary()` still path now `out/gallery/stills/style-<slug>.jpg`.
- `plugin.yaml`, `__init__.py`: `veasy_brush_book` at the end of the lists.
- `tests/test_plugin.py`: `brush-book` added to `SKILLS`.
- `skills/make-video/SKILL.md`: the Visual Catalogue line.

Proposed paragraph for CLAUDE.md: "**The brush book** (`tt_shorts/gallery.py`, `examples/`, `veasy:brush-book`): every
picture is a real render, read from data (brushes, `variety.OPTIONS`, directors, styles, rubrics, plate posters) and cached
by hash; no item is drawn by hand. A new brush, option or plate kind needs no change there. `examples/` films pass `check`
and each pair's bad file fails with the line named in its `check_says`."
