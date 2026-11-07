---
name: brush-book
description: "Use when you must choose WHAT a story should look like: which scene brush, hook, motif, entrance, transition, director, style or rubric fits what the story needs, and you want to see a real rendered frame first. Also for annotated example films and bad-to-fixed pairs to learn the reasoning. Examples: \"which scene shows a single number\", \"what are my options for a place\", \"show me how a law story is built\", \"why did my story fail check\""
---

# The brush book

A catalogue of **real renders**: every picture is a frame the engine drew (nothing is a mock-up), with the command
for it and when not to use it. It reads brushes, variety options, directors, styles, rubrics and baked plates from
data, so a brush, block, template or plate merged later appears by itself after a rebuild (a test adds fixtures to prove it).

## The one line

```bash
python -m tt_shorts.engine gallery --find "a number"
```

You get the five best entries as JSON: `id`, `type` (brush, hook, motif, entrance, transition, director, style,
rubric, block, template, plate), `need` (when to use it), `command`, `still` (a path under `out/gallery/`) and `when_not_to_use`.
Open the `still` and look at it before you choose. The first match is usually right; read `when_not_to_use` of the
first two before you commit.

A person opens `out/gallery/index.html` instead: a search box ("a number", "a place", "a process"), a filter per kind,
a light/dark switch, the picture of every brush in each look and theme, a copy button for the command.

## Ask the way a story speaks

| The story has | Ask | Usually |
|---|---|---|
| one figure that carries it | `"a number"` | `stat` |
| a place | `"a place"` | `where` |
| steps or a procedure | `"a process"` | `steps`, `checklist` |
| two things against each other | `"compare two things"` | `compare`, `versus`, `pair` |
| a part of a whole | `"percent of a whole"` | `share`, `budget` |
| a series over time | `"change over time"` | `trend`, `change` |
| an exact sentence somebody said | `"a quote"` | `quote` |
| an order of places | `"a ranking"` | `ranking` |
| dates, a window, a deadline | `"dates and a deadline"` | `timeline`, `calendar`, `countdown` |

Pick the brush whose **shape** is the fact's shape. When two are close, the sibling that draws the exact shape wins
(ranking over bars, budget over share). A story of three to six scenes starts with `hook`; use as few brush types as
tell it.

## The three-try rule

1. `gallery --find "<the need in a few words>"`; look at the first still.
2. Not it? Read `when_not_to_use`, then ask again with the other word (a number, a count, a price).
3. Still not? `gallery --find "<the kind>"` with `kind` words (a hook, a transition) or open the page and filter.

If three asks give nothing fitting, the story may need a brush that does not exist yet: say so in your result, do not
bend a brush to a fact it was not made for.

## What the book shows, and what it does not choose

- **Brushes** (31 today, more after merges) are shown in every look (editorial, kinetic, cards) and theme (dark,
  light) of the default pack. The scene JSON beside each is the brush's own `example`: copy its **keys**, write your
  own text, keep the Georgian limits.
- **Hooks, motifs, entrances, transitions** are options the engine picks by itself (`variety`: the least used lately).
  The book shows them so you know the vocabulary; **do not force one by hand**. A film in the same style as its
  neighbours is the failure the variety rule exists to prevent.
- **Directors, styles, rubrics** are named choices. A director changes the shape of the same facts; a style a film's
  look; a rubric is a named show. Their cards say when not to use them. A style card is the kit's preview with the
  style's own picks; a style of the other engine (HyperFrames) is drawn here as the kit shows its picks, not as that
  engine would compose it.
- **Blocks and templates** are the HyperFrames side: a block (`compose/blocks/`) is one composed scene with bound
  slots, a template (`templates/`) an approved film to follow. Their picture is a real `compose look` frame strip with
  the slots filled by their own examples; the command is `compose scaffold <story> --blocks <id>` or `--template <id>`.
- **Plates** appear when someone has baked `plates/<kind>/poster.png`. They are grey, hold no text, and are never for
  news, crime, incidents or deaths.

## Learn from examples, not by copying

```bash
python -m tt_shorts.engine gallery --examples --seed <your story id>
```

Gives three annotated films and one bad-to-fixed pair, rotated by the seed (a different seed, different ones; the
same seed, the same ones). Each film says:

- **asked**: what the story needed to tell,
- **shape**: why its scenes are these scenes,
- **turned_down**: what looked possible and was refused, and why,
- **learn**: the one rule to take away.

Copy the reasoning, never the scenes or the order: the films in `examples/` are for reading, and a new film that
copies one is one more film in the same style as the rest. A pair shows a story that fails `engine check`, the line the check
says, why, and the fix:

```bash
python -m tt_shorts.engine check examples/pairs/<id>-bad.json     # fails with the line in `check_says`
python -m tt_shorts.engine check examples/pairs/<id>-fixed.json   # passes
```

`examples/index.json` lists all 12 films (news, digest, explainer, law, story and a rubric, in two packs) and 6 pairs.

## Rebuild the book

```bash
python -m tt_shorts.engine gallery --real        # renders what is missing or stale, then writes the page
python -m tt_shorts.engine gallery               # only the page, from what is already rendered
```

`--real` costs machine time (about ten minutes the first time on 8 cores, seconds when nothing changed), no tokens
and no money: stills only, silent, no voice, no network. Pictures are cached by a hash of what draws them (the item's
data, the brand pack, Remotion's source), so only what changed is redrawn. Run it in the background; do not read its
output. `--only brush` limits it to one kind; `--limit 2` is a trial.

## Rules the book keeps

- A picture is a real render or it is absent: a missing item shows no picture rather than a drawn one.
- The text on the pictures is a placeholder sentence plus the brush's example; it is not a claim about anything.
- No client's name, colour or link belongs in anything the book writes: it reads the default pack.
- Related: `veasy:write-script` (the brush table and how to fill slots), `veasy:formats` (looks, transitions, themes),
  `veasy:directors`, `veasy:styles`, `veasy:rubrics`, `veasy:qa`.
