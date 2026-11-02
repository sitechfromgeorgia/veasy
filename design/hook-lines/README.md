# The hook's line breaks are a typographic decision, not a character count

Found by Sizmara while rendering the demo story (`engine still stories/veasy-demo.json --look cards
--engine silent`): the first frame of the video had a **line of one word** in the middle of the block.

## What was wrong

`writer._wrap_hook()` broke the headline with `len(cand) <= limit` per line. On Georgian that is a blind
count: it cuts wherever 22 characters run out, so a short word is left alone on a line and a line can end
on a word that belongs to the next one. The demo head came out as

    Veasy ამბიდან      ← 13 chars
    ვიდეოს             ← 6 chars, one word: a hole in the block
    თავად აწყობს       ← 12 chars

Georgian is unicase and has no hyphenation, so nothing can re-balance it later: whatever the writer
produces is what the viewer sees at 108px.

## What changed

`tt_shorts/writer.py` now has `hook_lines(lines, limit=22, max_lines=4)`, and `_wrap_hook()` calls it.
It scores every split into 1–4 lines and takes the best by this order:

1. **no holes** — a line of one word, or a line ending on a hanging word (`და`, `რომ`, `თუ`, `რადგან`…),
2. **fewer lines** — the composition's `fitSize` grows the type when the widest line is narrower,
3. **narrowest block** — the smallest widest line among those.

Words are never changed, reordered or dropped; a head that fits on one line stays on one line.
`tests/test_hook_lines.py` covers all of it (6 tests); the full suite is 121 tests, `tsc` clean.

## Measured on the demo head

| split | lines | widest line at 100 px | type size in the frame |
|---|---|---|---|
| old, character wrap | 3 (one of them 1 word) | 717.6 px | 120 px |
| new, balanced | 2 | 779.1 px | 108 px |

Slightly smaller type, no hole. If the type has to stay at 120 px and above, the **head has to be
shorter** — 33 characters is already three lines at this width. That is a copy decision, not a break
decision, and it is the one thing a break algorithm cannot fix.

## Design rule for anyone writing a story

- A hook head is 2–3 lines and **at most ~28 characters**; anything longer starts to read as a paragraph.
- Write the head as phrases that can stand alone; the breaker keeps them whole but cannot invent a pause
  where the copy has none.
- Never let the head end on „და" / „რომ" — the last word of a head is read as the punchline.
