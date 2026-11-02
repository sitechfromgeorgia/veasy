---
name: rubrics
description: "Use when a Veasy video should be one of the named recurring shows (rubrics) with an episode number, when making the morning digest, when asked which rubric a story fits or why it got one, or when adding a rubric. Examples: \"make today's number of the day\", \"queue the morning digest\", \"does cluster 24835 fit a rubric\", \"why is this video #12\", \"add a weekly rubric\""
---

# Rubrics (named recurring shows) and the morning digest

A **rubric** is a show the audience learns to recognise: the same name, shape and hour every day, with an episode
number. Code decides it (`tt_shorts/rubrics.py`, `rubrics/<id>.json`); the writer never sets a rubric, an episode or
a part. A rubric's video draws a chip in the hook, „დღის ციფრი · #12“, from code's text.

| id | chip | what | shape | slot |
|---|---|---|---|---|
| `digest` | დილის N ამბავი · #e | 2-3 checked stories in one 45-60 s video; no writer | hook, chapter + its scenes per story, end | 08:00 |
| `changes` | რა იცვლება · #e | service news with a date and a price, a rule or a place | hook, 2-4 scenes (one dated: timeline, rail or steps), end | 10:00 |
| `number` | დღის ციფრი · #e | one stated number of 100+ (or a percent), 20-25 s | hook, stat/change/share/compare, 1-2 scenes, end | 13:00 |
| `agree` | ადასტურებს N გამოცემა · #e | the facts literally in 3+ member articles; „მინიმუმ N“ | hook, agree, 0-2 scenes, end | 16:00 |
| `continues` | ამბავი გრძელდება · ნაწ. N | a cluster that had a video and since gained 2+ outlets and a new number or quote | hook, 2-4 scenes, end | 18:00 |

```bash
python -m tt_shorts.engine rubrics facts --source tbilisi-today --ref 24835   # which rubrics a cluster fits, and why
python -m tt_shorts.engine write --rubric number --ref 24835                   # written, checked, stamped (#episode)
python -m tt_shorts.engine queue add --ref 24835 --rubric number               # its format (number: 20-25 s) by default
python -m tt_shorts.engine queue add --rubric digest --ref done:tbilisi-today[:2026-11-02]   # the morning digest
python -m tt_shorts.engine write --rubric digest --source stories --ref a.json,b.json        # or from story files
python -m tt_shorts.engine rubrics stamp <story.json> --rubric number [--sources articles.json]  # a hand-written one
python -m tt_shorts.engine rubrics list [--brand tbilisi-today]                # the rubrics and the episode counters
python -m ops.daily --limit 10 --rubrics                                       # the day's picks get their rubrics
```
Tools: `veasy_rubrics` (list, facts, stamp); `veasy_write` and `veasy_queue` take `rubric`.

## How code decides

- **Eligibility** is data: `eligible` is a list of alternatives, each `{fact: minimum, "families": [...]}`; `never`
  rules it out. Facts code finds: `big_numbers`, `prices`, `rules`, `dates`, `places`, `outlets`, `members`,
  `agreed`, `had_video`, `new_outlets`, `new_facts`, `stories`, plus the directors' (`veasy:directors`). A rubric that
  doesn't fit is refused before the writer runs (`write --rubric agree` on a one-article story fails).
- **Once a day each:** `ops/daily.py --rubrics` gives each rubric to the first pick it fits (continues, agree, number,
  changes), a story at most one; a rubric job's priority follows its slot, then one digest job of yesterday's done
  news videos.
- **Episodes:** reserved when code stamps the story (before the voice, because the chip shows it), the same number for
  the same story every time (another look, a re-run). The queue marks it done when the job ends done; a failed or
  cancelled job gives the number back if no later episode exists, else it stays unused (a gap, never two videos with
  one number). Per brand and rubric, in `veasy.db`.
- **Continues:** every news job that ends done stores what its cluster had (its outlets, the stated quantities and
  quotes of its articles). A later run compares the cluster with that: 2+ new outlets and a number or quote that
  wasn't there make part N+1, and the story must say at least one of the new things.
- **Agree** (news rule N12): code counts, across all member articles (one per outlet), the facts that are literally
  in at least 3: the same number with the same word, day and month, time, place or quote. The agree scene shows up to
  3 of them, `n` is the smallest count („მინიმუმ 4“, never „all“), the narration says „მინიმუმ“ and N in words, and no
  outlet is named or called by a side anywhere in the video.
- **Digest:** source `stories`, program `digest`, no model. Code re-checks each story, opens each with a chapter
  card (its number of the total, its category, its own hook lines), takes its first sentences up to its outlets line
  and its scenes that start there (at most 2), adds the intro („დილის ორი ამბავი ერთ ვიდეოში: ...“) and the outro, and
  grows the sentences until the estimate is 47-57 s. The label says the real count: 2 stories make „დილის 2 ამბავი“.
  Mixed brands and a story twice are refused. The whole digest is checked again (news rules, Georgian, timing).

## Add a rubric (no code)

1. `rubrics/<id>.json`: `label` (Georgian, no digit; `{n}` with a `count`), `about`, `numbering` (episode | part),
   `program`, `format`, `slot` (HH:MM), `eligible`, `never`, `shape` (`[{"types": [...] | "any", "min", "max"}]`,
   hook first, end last), optional `needs`, `brief` (2-10 lines for the writer), optional `words`.
2. A new length is a format in `formats/` (`veasy:formats`).
3. `python -m tt_shorts.engine options` must not fail; a case in `tests/test_rubrics.py`.
