# Veasy Scenario Schema Specification (Goal 6)

## Overview

A **scenario** defines a dramaturgical plot and narrative arc for a video.
Unlike directors (which shape visual styling and motion) or rubrics (which define recurring daily shows), a scenario governs *how a story unfolds*:
- what it promises to the viewer,
- how tension, context, or curiosity builds,
- where the story turns or tests a false assumption,
- when the payoff or core revelation is delivered,
- and how it resolves into actionable understanding.

Scenarios live as declarative JSON files in `scenarios/<id>.json`.
Eligibility and gate checking are pure data evaluations without code execution, reusing `tt_shorts.rubrics` logic cleanly.

---

## 1. Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | **Yes** | Unique identifier matching filename: `^[a-z0-9-]+$` |
| `title` | `string` | **Yes** | English title (e.g. `"Guess the Number"`, `"Myth vs Fact"`) |
| `label` | `string` | **Yes** | Georgian label for on-screen chips or UI (e.g. `"გამოიცანი რიცხვი"`) |
| `about` | `string` | **Yes** | English summary of the narrative plot and agent instructions |
| `eligible` | `list[dict]` | **Yes** | Declarative condition list (OR of ANDs, matching `rubrics.holds`) |
| `never` | `list[dict]` | **Yes** | Declarative exclusion conditions (any match refuses the scenario) |
| `beats` | `list[dict]` | **Yes** | Ordered list of 3-7 narrative beats |
| `pacing` | `dict` | **Yes** | Target narration word count and duration window |
| `brief` | `list[str]` | No | Optional writer lines instructing the model on beat execution |
| `requires_correction` | `bool` | No | Flag requiring document-verified correction (auto-enabled for `myth-vs-fact`) |

---

## 2. Beat Specification (`beats`)

Each beat in `beats` represents one scene in the video's dramaturgical sequence.

| Beat Field | Type | Required | Allowed Values / Format | Description |
|---|---|---|---|---|
| `id` | `string` | **Yes** | `^[a-z0-9_-]+$` | Beat identifier (e.g. `"hook"`, `"false_lead"`, `"turn"`, `"reveal"`) |
| `job` | `string` | **Yes** | One of: `promise`, `setup`, `context`, `complication`, `false_lead`, `evidence`, `turn`, `payoff`, `resolution` | The narrative role of this beat |
| `scene_types` | `list[str]` \| `"any"` | **Yes** | Catalog brushes (e.g. `["stat"]`, `["points", "pair"]`) or `"any"` | Brush types allowed for this scene |
| `word_budget` | `[int, int]` | **Yes** | `[min_words, max_words]` where `0 <= min_words <= max_words <= 50` | Spoken narration word budget for this beat |
| `sound` | `string` \| `null` | **Yes** | `"click"`, `"pop"`, `"whoosh"`, `"tick"`, `"thud"`, `"blip"`, `null` | Synthesized SFX cue for this beat |
| `fact_gates` | `dict` | No | `{fact: min_count}` (e.g. `{"numbers": 1}`) | Required facts in this scene's text/narration |
| `payoff_held` | `bool` | No | `true` or `false` (default `false`) | If `true`, the payoff reveal must NOT appear before this beat |

### Beat Jobs

1. `promise`: The hook / opening. Hooks the viewer with a question, mystery, or stakes.
2. `setup`: Establishes the baseline status quo or context.
3. `context`: Historical, situational, or domain background.
4. `complication`: The obstacle, tension, puzzle, or unexpected shift.
5. `false_lead`: The common misconception or intuitive assumption that is disproven.
6. `evidence`: Concrete proof, data, measurements, quotes, or examples.
7. `turn`: The pivotal counter-intuitive insight, pivot, or reversal.
8. `payoff`: The reveal, punchline, core statistic, or verdict.
9. `resolution`: Consequence, call-to-action, or takeaway.

### Sound Cues

Sound cues are strictly synthesized from `tt_shorts.sfx` / `tools.compose_sfx`:
- `whoosh`: Sweep / cut motion accent.
- `pop`: Visual reveal or mark landing.
- `tick`: Mechanical count / anticipation step.
- `thud`: Impactful landing or finality.
- `click`: Crisp latch or transition snap.
- `blip`: Data item emergence (bars, compare).

---

## 3. Pacing (`pacing`)

Controls overall story length and reading rhythm:
```json
"pacing": {
  "target_words": 80,
  "min_seconds": 25.0,
  "max_seconds": 45.0
}
```
`target_words` can also be a range: `[70, 95]`.

---

## 4. Eligibility and Condition Grammar (`eligible`, `never`)

Reuses the exact declarative grammar from `tt_shorts.rubrics`:
- **Counts**: `{"numbers": 1}`, `{"quotes": 2}`, `{"big_numbers": 1}`, `{"prices": 1}`
- **Maximums**: `{"numbers": {"max": 0}}`
- **Families**: `{"families": ["economy", "society"]}`
- **Flags**: `{"deaths": false}`, `{"verified_correction": true}`
- **Programs**: `news` is universally excluded.

---

## 5. Free Plan Checks (`check_plan_beats`)

Evaluated at `engine plan` before any voice or render cost:
1. **Scene type validation**: Each story scene type must match the beat's allowed `scene_types`.
2. **Word budget validation**: Narration words spoken in each scene must fall within `[min_words, max_words]`.
3. **Fact gates**: Scene text and narration must satisfy required fact minimums.
4. **Early payoff check**: Verifies the payoff number/name is NOT spoken in narration before the payoff beat.
5. **Myth-vs-Fact gate**: Ensures the source document itself provides the correction (preventing editorial opinion under N1).
6. **Program check**: `news` program stories are refused.
