# Next: three briefs ready to hand to an agent

Written 2026-11-02 when the session's budget ran out. Each is a self-contained brief for one agent working in its
own branch. Read CLAUDE.md first. The design behind them is in ROADMAP section D and in the research summarized
there (brushes, directors, HyperFrames motion rules).

Rules for every brief:
- Verify with `python -m unittest discover -s tests`, `(cd remotion && npx tsc --noEmit)` and
  `python -m tt_shorts.engine probe <story> --look all`, then look at the stills.
- After a visual change, run `engine selftest`; use `--update` only for intended changes.

## 0. Directors (first: the owner's "separate agents each choose a different direction")

Done on 2026-11-02 (`directors/`, `tt_shorts/directors.py`, skill `veasy:directors`), with the novelty guard and
the three-director demo below.

Language models drift toward the same choices when asked to "be creative", so code assigns a creative director
before the writer runs. A director changes what kind of film a story becomes; it never touches facts, the palette,
the safe zone or the news rules.

- **Data.**
  - `directors/<id>.json`, validated by `tt_shorts/directors.py` and listed by `engine options`.
  - The eight directors:

    | id | Georgian label |
    |---|---|
    | data | ციფრი |
    | map | რუკა |
    | type | სიტყვა-დარტყმა |
    | draw | ესკიზი |
    | chronicle | ქრონიკა |
    | witness | ციტატა |
    | brief | მოკლედ |
    | single | ერთი კადრი |

  - Each director has:
    - a Georgian label;
    - an English brief (6-10 lines for the writer);
    - eligibility from facts that code extracts before writing (numbers, dates, `geo.locate` places, quote
      candidates, `icons.find` matches, the family);
    - its allowed scene types with weights;
    - hook, motif and transition subsets;
    - a motion personality (spring numbers, enter and stagger frames, a "current" direction);
    - its pacing and "never" gates. The Typographer never does politics, crime or deaths; the Witness shows two
      speakers when the cluster quotes two sides.
  - A test checks that every family has at least 2 eligible directors.
- **Assignment.**
  - `variety.direct()` picks the least used eligible director among the brand's last 20 (the `variety` table gets
    a `director` column).
  - `engine.write_story` stores it as a code-owned `story["director"]`.
  - The writer prompt gets that director's brief, only that director's scene types and the extracted facts.
  - `render --director` and `queue add --director` override it.
- **Render.**
  - `variety.pick()` chooses within the director's subsets.
  - `props.style` gets `director`, `motion` and `current`.
  - `ui.tsx` `useIn`/`In` read the motion numbers (defaults unchanged).
  - Entrances and cuts follow the current.
- **Novelty guard.** Done (`variety.choose`, `tests/test_variety.py` NoveltyGuard).
  - A fingerprint of a planned video: director, scene sequence, hook, motif, enter, transition, music.
  - `similarity` counts the shared fields, 1 each; the scene orders count as their difflib ratio.
    `distance = 1 - similarity / 7`.
  - Too close is 5 of 7 shared with one of the brand's last 20 (not the story's own renders). Then the picks are
    re-rolled inside the director's subsets, least overused first, at most 64 tries, deterministic per story.
  - It runs in `props.choose`, which `props.build` calls before `speech.voice`, so `render`, the queue, `still`,
    `probe` and `engine plan` all pass it before any TTS. `engine plan` shows the fingerprint and the closest
    recent video and records nothing. If nothing is far enough, the farthest is taken with a warning in the render result; it never fails a
    video. A re-render keeps its picks.
  - The `variety` table gains `novelty` (the distance) and `rerolls` (safe migration); `report()` gives the
    average distance. The pure functions (`fingerprint`, `similarity`, `distance`, `assess`) are for `engine plan`.
- **Demo.** Done: `stories/24835-data.json`, `24835-map.json`, `24835-brief.json`, the gas cut under three directors.
  Each passes `engine check --sources tests/fixtures/sources.json` (with kaeasy too) and `engine probe --look all`.
  - data: the number first; hook → stat (the longest hold) → timeline → sources → end.
  - map: the place first; hook → where (Tbilisi map, both districts pinned) → sign (gas, stops) → timeline → end.
  - brief: a service card; hook → points (who, where, why) → steps (when) → sources → end.

## 1. The brush kit (new brushes + one catalog that generates the writer's menu)

Done on 2026-11-02: `brushes/<type>.json` for all 20 types, `tt_shorts/catalog.py`, `tt_shorts/marks.py`,
`remotion/src/marker.tsx` and `scenes/brushes.tsx`, N11 in `news_check.spoken`, the demo
`stories/veasy-brushes.json`. Code picks the mark's kind (the brush's kinds, varied per story; a number or a
link's edge is underlined) and the strokes (clean, rough only for sports and culture). The spec it was built to:

- **Marker, emphasis synced to the voice (C2).**
  - Any content scene may carry `"em": "<phrase>"`. The phrase must be in that scene's on-screen text and in its
    part of the narration; code checks both.
  - `speech.py` resolves it to a time from the word timings, and a mark draws on the phrase at that moment.
  - Use `@remotion/rough-notation@4.0.539` (MIT). Kinds: underline, box, circle, highlight, bracket.
  - Clean strokes for hard news, a little roughness for light news. Ink by default; at most one per scene.
- **New scene types, each through the full CLAUDE.md checklist:**
  - `share`: a 10×10 grid. The percent must be stated with "%" in the articles.
  - `rail`: 2-4 dated events, and the dot travels the rail. Dates must be in the articles; code checks the order.
  - `compare`: two magnitudes as true-proportion squares. Same unit; ratio ≤ 40, else use bars.
  - `link`: who meets whom. 2-3 nodes with initials, joined by an edge labelled with a verb said in the narration.
  - `stat.style`: count | wheel (odometer) | flap (split-flap; never for politics or crime).
- **The catalog.**
  - `brushes/<type>.json` for every scene type: what, use_when, avoid_when, pairs_with, typed slots with
    Georgian length limits, families deny, min_seconds, min_words, an example.
  - `tt_shorts/catalog.py` generates from it:
    - `engine.SCENES`;
    - `speech.MIN_SCENE`;
    - `ka_check.MIN_WORDS`;
    - the writer's schema lines, with `catalog.schema(types)` so a director can limit the menu;
    - the options block.
  - A test checks the generated tables equal today's.

## 2. Rubrics and the morning digest (D6 + B7)

Done on 2026-11-03 (`rubrics/`, `tt_shorts/rubrics.py`, `tt_shorts/digest.py`, source `stories`, program `digest`,
scenes `agree` and `chapter`, rule N12, tool `veasy_rubrics`, skill `veasy:rubrics`). Decisions made on the way:
- Episodes are reserved when code stamps the story (the chip is drawn before the voice), idempotent per (brand,
  rubric, story); done when the job ends done; a failed or cancelled job gives its number back only when it is
  the last (else a gap, never a number twice).
- "Continues": every news job that ends done stores its cluster's outlets, stated quantities and quotes; growth is
  compared with the latest stored part.
- Agree counts per outlet; a fact is the same number + word stem, day and month, time, gazetteer place or verbatim
  quote; N is the smallest count shown. Agree and chapter are filled by code (no writer schema line).
- The digest takes 2-3 stories (owner's lead, 2026-11-03: never claim three when there are two); its label is
  „დილის N ამბავი“. Demos: `stories/rubric-24835-number.json`, `stories/digest-2026-11-01.json` (24835 + 24725).
  A real three-story demo needs a third cluster's articles, which only the server's D1 has.

The spec it was built to:

- **Data.** `rubrics/<id>.json` holds:
  - a Georgian label, drawn as „დღის ციფრი · #12";
  - its format;
  - an eligibility predicate that code evaluates on the cluster's data;
  - the allowed scene shape;
  - a writer brief addition;
  - a time slot.

  `tt_shorts/rubrics.py` loads and validates them and keeps an episode counter per brand in `veasy.db`.
- **The rubrics:**
  - „დღის ციფრი": a striking stated number; hook → stat/change → 1-2 scenes → end; 20-25 s.
  - „რა იცვლება": service news with a date and a price, a rule or a place.
  - „ამბავი გრძელდება · ნაწ. N": a cluster that already had a video and has since gained 2+ outlets and a number
    or quote not in part 1. Code compares against the stored state.
  - „ადასტურებს N გამოცემა": a new `agree` scene showing the facts that are literally in at least N member articles.
    Code counts across all members; it says „მინიმუმ N" and never labels outlets by side.
  - „დილის 3 ამბავი": three checked stories of the day in one 45-60 s video, with a new `chapter` scene and one
    narration built by code from their first sentences. A `digest` program with source `stories`.
- **Wiring.**
  - `ops/daily.py --rubrics`;
  - `engine queue add --rubric`;
  - the plugin and a skill.

## 3. Storyboard before paying, motion rules as checks, a drawing library

Done on 2026-11-02: `engine plan` (`tt_shorts/plan.py`, tool `veasy_plan`), `tt_shorts/motion_rules.py`,
`tt_shorts/drawings.py` with 18 seeds in `assets/drawings/`. The spec it was built to:

- **`engine plan <story>` (B2).** A free storyboard that runs before any voice is paid for:
  - per-scene times, words and reading load (each text on screen ≥ 0.5 s + 0.3 s per word);
  - the variety picks;
  - the probe;
  - a half-size contact sheet.

  Tool: `veasy_plan`.
- **`tt_shorts/motion_rules.py`.** The HyperFrames rules as checks:
  - a text on screen too briefly;
  - more than 3 s with nothing changing;
  - more than 3 transition kinds;
  - ping-pong cuts;
  - two scenes of the same type in a row.

  They are warnings in `plan`, and only the unreadable-text rule holds a render.
- **A drawing library.**
  - Every drawing that passed `art.sanitize` and `art.quality` in a video that ended `done` is saved per motif.
  - When a new drawing fails, a library drawing with the same motif is used before the scene is dropped, with its
    labels re-checked.
  - Seed it with `assets/drawings/*.json`: 12-20 hand-made line drawings (gas pipe, bus, school, hospital, court,
    bridge, power line, tap, house, car, ballot box, phone, money, factory), each passing sanitize and quality.
