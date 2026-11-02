---
name: queue
description: "Use when making more than one video, a daily batch, or a video that should be made later or retried: the Veasy job queue, where files are kept and what they are called. Examples: \"queue today's stories\", \"what failed last night\", \"retry job 3f2a9c1e0b7d\", \"where is the mp4 of 24725\""
---

# The queue and the storage

One video is one **job**: (brand, program, source, ref, format, overrides). The job id is a hash of exactly that, so
adding the same request twice returns the same job: you can't make the same video twice by accident. Every command
prints JSON. Tool: `veasy_queue` (same arguments as the CLI).

```bash
python -m tt_shorts.engine queue add --source tbilisi-today --ref 24725 [--brand tbilisi-today] [--format news]
python -m tt_shorts.engine queue add --program law --ref constitution:17     # a program (veasy:programs): its first
                                                                             # source and its format by default
python -m tt_shorts.engine queue add --story /path/story.json --brand sitech --format news-roll   # already written
python -m tt_shorts.engine queue list [--state failed]      # newest first, plus counts per state
python -m tt_shorts.engine queue run [--max 5]               # one worker at a time; a second one answers busy
python -m tt_shorts.engine queue show <id> | retry <id> | cancel <id>
```

## States

```
queued -> writing -> rendering -> done      QA passed, real voice: ready to publish (result.file, result.qa)
                              \-> held      rendered, but QA found problems or it was a preview voice
                                            (`queue run --engine silent|edge`): a person looks (error says what)
              any step -------> failed      error_class + error; fix the cause, then `queue retry <id>`
cancelled: taken out by hand
```
`error_class`: `transient` (network, 429, 5xx, timeouts: re-queued by itself after 5, 10, 20 min, then failed),
`config` (a key, a format or a brand pack is wrong), `content` (the story failed a check: fix the story, never the
rule), `layout` (scene timing), `render` (Remotion or ffmpeg: read the log line), `review` (`held` only: QA passed,
but the job's program says `publish: review`, e.g. law and explainer; a person watches it before it goes out).
Higher `--priority` runs first. A story job takes the story's own `program`.

## Where things are (VEASY_HOME, default <veasy>/data)

```
veasy.db                                   the queue and the cost ledger (SQLite)
stories/<brand>/<day>/<ref>.json           the story; <ref>.sources.json beside it (the articles)
renders/<brand>/<day>/<ref>-<format>-<look>-<captions>.mp4
                                           + .json (what was rendered, with which voice and kaeasy) + .sheet.jpg
                                           + .props.json (what Remotion drew) + -package/ (veasy:package)
cache/voices/<sha16>/                      one voice track per (engine, voice, style, spoken text): re-renders free
cache/work/<job>/                          scratch, deleted after a good render
logs/<day>.jsonl                           one JSON line per event (queued, written, rendered, failed, gc)
```
Names are lowercase ASCII with hyphens; `day` is the server's date when the work was done. A job is named
`<brand>-<ref>-<format>` (e.g. `tbilisi-today-24725-news`). `python -m tt_shorts.engine gc` deletes scratch after
2 days, renders after 30, voices and logs after 90; stories are kept (they are the record of what was published).

## Daily batch

`python -m ops.daily --limit 6 --run 6` picks tbilisi.today's stories (4+ outlets, last 18 h, category caps,
no repeats), queues them and runs the queue. `--dry-run` shows the picks only. Cron or timers need the owner's OK.
