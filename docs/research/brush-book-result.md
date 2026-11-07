# Brush book: result

Lane `goal/brush-book`, worktree `D:\MyStaff\Veasy-brush-book`. Antigravity ran out of quota after the research;
Claude Code built everything below. Rebase onto main is left to the integrating session.

One line for the user: `python -m tt_shorts.engine gallery --find "a number"` gives the best entries as JSON (id, kind,
real still, command, when not to use); `gallery --real` renders and writes `out/gallery/index.html`.

## Done when

| # | Line | Status | Evidence |
|---|---|---|---|
| 1 | A test finds a real file for every brush x look x theme and every other listed item | done on this machine | `engine gallery --real` made 257 files in 741 s, 0 problems (31 brushes x 3 looks x 2 themes = 186 stills, 8 hooks, 10 motifs, 8 entrance strips, 14 transition strips, 8 directors, 18 styles, 5 rubrics). `tests/test_gallery.py::RealFiles` checks every promised file is a real image (skips where `out/gallery` is not rendered: `out/` is not in git). Plates: listed only when `plates/*/poster.png` exists (none on this branch). |
| 2 | The page opens and search works at phone and desktop width | done | Served over http (port 31080) and driven in the built-in browser at 390 px and 1280 px: no horizontal scroll, 1 column on the phone and 3 on desktop, images load, filters and the light/dark switch work. Queries "a number", "a place", "a quote", "compare two things", "a ranking", "percent of a whole" put the right brush first; "a process" puts `steps` first; nonsense shows "0 shown" and the empty message. |
| 3 | A sub-agent given a story and only this page picks a sensible look in under 3 tries, for 5 stories | done, 4 clear and 1 arguable | A Haiku agent given only the skill and `gallery --find` (not the code) picked, in 1 try each: water cut -> `sign` (arguable: `stat` for 3200 households is the more natural pick; it named stat as runner-up), exact quote -> `quote`, five ranked resorts -> `ranking`, quake region -> `where`, passport renewal -> `steps`. 5 of 5 within 3 tries. |
| 4 | 12 examples and 6 pairs exist and pass `check` | done | `examples/index.json`; `tests/test_gallery.py::Examples` runs `engine.check_story` on all 12 films (must be empty) and on every pair (bad fails with the line named in `check_says`, fixed is empty). |

The cold user got `--find` and the skill, not the HTML page itself (an agent cannot run the page's script); the page and
`--find` share the same words and need-scores (`gallery.SYNONYMS`, `need_score`).

Gates: the full unit suite was run once on the last commit (result line below); `tsc` and `selftest` were not run
because no Remotion or scene code was touched (only Python, JSON, docs and a skill).

GATES_LINE

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
3. the last commit of the branch (`git log -1`): in-page search ranking fix, result file.

## Not done, and why

- Short mp4 clips: entrances and transitions are frame strips instead. A strip is real and shows the motion in one
  picture; clips need a full render per item (about 40 more renders). Add under `--clips` later if the owner wants them.
- Composed HyperFrames blocks (9) and templates (3) are not in the book: showing them needs a HyperFrames render per
  item, and this branch has no baked posters for them. They are not listed rather than drawn by hand.
- Plates: no poster exists on this branch, so none is listed. When another lane bakes `plates/<kind>/poster.png`, it
  appears on the next rebuild (test: `test_plate_posters_are_read_from_disk_when_they_exist`).
- The HyperFrames-engine styles are drawn through Remotion with the style's own picks (the card says so); they are not
  that engine's compose of the style.
- Text on the stills is the brush's example plus a placeholder sentence in the captions: it claims nothing.

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
