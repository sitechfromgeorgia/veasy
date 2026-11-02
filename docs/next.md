# Next: three briefs ready to hand to an agent

Written 2026-11-02 when the session's budget ran out. Each is a self-contained brief for one agent working in its
own branch. Read CLAUDE.md first. The design behind them is in ROADMAP section D and in the research summarized
there (brushes, directors, HyperFrames motion rules).

Rules for every brief:
- Verify with `python -m unittest discover -s tests`, `(cd remotion && npx tsc --noEmit)` and
  `python -m tt_shorts.engine probe <story> --look all`, then look at the stills.
- After a visual change, run `engine selftest`; use `--update` only for intended changes.

## 1. The brush kit (new brushes + one catalog that generates the writer's menu)

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
