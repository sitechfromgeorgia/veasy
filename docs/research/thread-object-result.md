# Thread object: result

Branch `claude/thread-object-ef75d6`. Research: `docs/research/thread-object.md`.

## Done when

| Line | State | Evidence |
|---|---|---|
| One line gives a film: object in 3+ scenes, changes state | done | `python -m tt_shorts.engine render stories/veasy-thread.json --engine silent`: 35.4 s, object in 5 scenes, state `grow`. `engine thread stories/veasy-thread.json` shows the plan for free. Frames: `docs/research/thread-object-evidence/` (pairs 1 to 10), and FILMS below |
| catalog, scenes, engine, variety tests; options even; `news` refused | done | `tests/test_thread.py` and the four files. Each cut comes up once in a run of its look (`Cuts`). `state` is refused by N1, kept out of the news writer's menu, `match`/`object` need a thread |
| flash, motion rules, layout probe in every look | done | FLASH below. Motion rules: no holds. Layout probe: 0 problems, 10 films, 3 looks (`tools/thread_pairs.py --check`) |
| One whole film rendered, passes `qa` | FILMS | FILMS below |
| Fresh-eye critic judged the ten pairs | done | "The critic" below: the object side won 4 of 10 |
| Full suite, tsc, selftest after the last fix | GATES | GATES below |

## Built

- `tt_shorts/thread.py`: the object from `concept`, a silhouette traced from any drawing, states drain, fill, break, grow,
  shrink, seats in Python (measured on real stories), a corner seat, `relieve` (a seat with text on it is given up
  before a render, so the thread never holds a video).
- `brushes/state.json`, `remotion/src/thread.tsx`, `remotion/src/scenes/state.tsx`, probe rule `seat`, `engine thread`.
- `match` and `object`: one more `variety` option each, only for a film with a thread, replacing nothing. No news video
  can get one: a format asking for one on a story without a thread gets the look's own cut.
- The `match` crash: `interpolate()` was given a backwards range (`[CROSS, 0]`). It hit every cut of every thread film, not
  only `match`; the probe's settled frames never reach a cut, which is why it stayed hidden. Fixed, with a test.

## The critic

Sonnet, sheets only, once, on the sheets of commit `8f2f44c`. Its picks against the key:

| Pair | Story | Critic chose | Its reason, shortened |
|---|---|---|---|
| 1 | explainer-inflation | kit | bigger type; the tag is decoration, tiny in three frames |
| 2 | law-constitution-17 | kit | steady and readable; the barrier is generic, tiny in frame 1 |
| 3 | bipi-draws | **object** | the drawing ties to the story; its cream fill glares |
| 4 | veasy-brushes | kit | varied, data led; a warehouse means nothing for new brushes |
| 5 | veasy-demo | **object** | varied scenes; the factory repeats, generic |
| 6 | veasy-icons | **object** (narrowly) | the valve fits the gas story; the faint corner icons are noise |
| 7 | veasy-new-01 | **object** | the torn banknote is a real metaphor on the budget frame; decoration elsewhere |
| 8 | veasy-new-02 | kit | a jar means nothing for registration or extradition |
| 9 | veasy-scenes | kit | a line chart and cards; the object's side looks lost |
| 10 | veasy-map | kit | the real maps carry the story; a drone makes them shallow |

**The object side won 4 of 10; the plan's bar for the owner's blind choice is 8.** The critic's three fixes:

1. Stop repeating one generic object across unrelated scenes: it reads as filler. Use it only where it carries the meaning.
2. Shrink the dead space and the tiny text, or fill the space with the point, not an icon.
3. Fix collisions and glare: the ghost quote mark, the cream fill, the faint corner icons, vague one-word titles.

What was done: the fill went from ink to the pack's muted tone (the glare), and the sheets were made again after it, so
they differ from what the critic saw only there. Not done: its fix 1 is the real finding. Where the object fit the
story (3, 6, 7) it won; where I forced a seed onto a demo story about Veasy itself (4, 8, 10) it lost. The picture needs
an object the story really has, and the object probably shouldn't stand in scenes that have their own picture (a map,
a chart). That is a change to `seat()`, and it pulls against "3 scenes"; see Owner decisions. The ghost quote mark is the
kit's own, not this lane's.

## Not done

- **HyperFrames blocks (item 5):** not built, this was not cheap. Missing: `flubber` in `compose/package.json` and in the
  allowed script list (`compose.py`, the `net` rule and the vendored copy in scaffold), one block per state and cut in
  `compose/blocks/`, a lint case in `tests/test_compose.py`, and `thread.outline` exposed to a composed film.
- The devices `graphic-match` and `object-wipe` in `concepts/devices.json` still list no scenes, so an idea can't name them:
  the two cuts come from `variety`, not from the idea.
- `stat` shows 4 for a value of 3.8 in `stories/explainer-inflation.json`. The kit's own, not touched here.

## Touches to shared files

`tt_shorts/engine.py` (options, `check`, the `thread` command, `relieve` in `render_story`), `tt_shorts/catalog.py`
(`NAMED_ONLY`), `tt_shorts/programs.py`, `tt_shorts/concept.py` (the idea's optional `drawing`, one prompt line),
`tt_shorts/probe.py`, `tt_shorts/motion_rules.py`, `tt_shorts/sfx.py`, `remotion/src/ui.tsx` (`Frame`), `remotion/src/NewsShort.tsx`,
`remotion/src/Probe.tsx`, `programs/explainer.json`, `concepts/devices.json`. `tests/test_concept.py`, `test_catalog.py`,
`test_scenes.py` changed for the new type. `news_check.IDEA_TYPES` sits next to plates-core's `MADE_PICTURE_TYPES`: expect a
small conflict there at merge, in `claims_check.py`, `programs.py` and the two allowlist tests.

## Proposed for CLAUDE.md

- **The thread** (`tt_shorts/thread.py`, `remotion/src/thread.tsx`, `veasy:direct`): a chosen idea's `object` gets a body: a
  drawing, a seat per scene computed in Python, a state by `verb`, one layer above the scenes. Never for news, crime,
  incidents or deaths. `state` is outside `news_check.SCENE_TYPES` and in `catalog.NAMED_ONLY`; `match` and `object` exist only
  with a thread (`variety.THREAD_TRANSITIONS`). A new scene type needs its height in `thread.CONTENT`. A form a match cut lands
  on is one closed path. The probe's settled frames never reach a cut: a change to the layer needs frames around a cut.

## Owner decisions

- The object stands in every scene with room today. The critic says it should stand only where it means something. Fewer
  scenes (the state scene and one or two others) would drop the "3 scenes" line. Which do you want?
- Pairs: 8 of the 10 stories are Veasy's own demo stories, about Veasy, and they suit an object badly. `veasy-map` also
  needed its scenes changed. The real news stories were left out on purpose. Is this enough for your blind choice, or do you
  want ten pairs on real non-news stories first?
