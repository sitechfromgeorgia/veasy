# Design audit — the SiTech brand in Veasy

Written 2026-11-02 by Sizmara (design), against the shipped code and the published brandbook
(`sitech-brandbook-ka-v1.pdf`, SiTech / Visual guide 1.0, 17 Oct 2026). No code changed: this is
evidence plus one proposed data file.

## 1. What is already right

- **Logo.** `brands/sitech/logo-horizontal.svg` and `logo-stacked.svg` are byte-identical to the
  official kit files (`sha256 28aca208…` and `d786ab5c…`). Nothing is re-typeset. Correct.
- **Typography.** One family per pack, FiraGO from `brands/_ka`, hierarchy by size and weight,
  no letter-spacing anywhere. That follows the brandbook's Georgian rules.
- **Layout tokens.** `remotion/src/brand.ts` keeps the frame bands, `SIDE`, `RADIUS`, and the safe
  zones (`SCENE_BOTTOM 1380`, `CAPTION_BOTTOM 1552`) in one place instead of per scene.

## 2. What is off-brand (measured, not an opinion)

`brands/sitech/brand.json` uses the palette of the older `sitech-shorts` pipeline, not brandbook 1.0:

| token | veasy `sitech` pack | brandbook 1.0 | verdict |
|---|---|---|---|
| canvas | `#171817` | Night `#05080F` (or Ink `#101313` as a soft dark) | off |
| ink | `#F1EDE4` (warm cream) | White `#FFFFFF` / Mist `#F8FAFC` | off |
| accent | `#FF792E` (orange) | Cyan `#00C8FF` (`#0076A3` on light only) | **not a brand colour at all** |
| muted | `#B6B4AC` | a step of the ink, not a second hue | off |

Contrast was never the problem (cream on `#171817` is 15.2:1, orange 6.8:1). The problem is identity:
the brandbook is **monochrome with exactly one cyan accent**, and orange is not in it. A SiTech video
therefore does not look like the SiTech site, the brandbook or the social cards, which all run on
`#101313 / #F8FAFC / #00C8FF`.

`remotion/src/brand.ts` also hard-codes the mistake in a comment — "the accent (tbilisi.today's red,
SiTech's orange)" — so the next person adding a look inherits it.

Try: `design/brand-audit/brand.sitech.proposed.json` (drop-in replacement, same keys, brandbook tokens).
Specimen: `design/brand-audit/specimen.png` (1800×1350, left = today, right = brandbook).

## 3. Design gaps worth closing (each is a small, separate change)

1. **A token file, not a token comment.** Sizes, weights, spacing and radii of the scenes live inside
   `NewsShort.tsx`, `scenes/index.tsx`, `scenes/more.tsx`. `brand.ts` holds only bands and `RADIUS`.
   Moving type sizes, weights and gaps into tokens makes a new look a layout change, not a restyle hunt.
2. **Two caption designs are not a caption system.** `page` and `roll` cover the two extremes. Missing
   the middle: a **phrase card** (one short phrase per shot, big, centred, no box) which is what most
   non-news vertical video uses, and a **lower-third** with a name/label for interviews.
3. **Accent semantics are undefined.** The brandbook says cyan = action/accent. In the scenes the
   accent is used for the caption underline, numbers, category chips and the end-card button — three
   meanings. One rule ("accent marks the number or the action, never decoration") is enough.
4. **No cover.** B3 in `ROADMAP.md` wants a cover PNG. A cover is a design asset, not a still: it needs
   its own composition (title 2 lines max, logo, date) at 1080×1920 plus 1280×720 for the blog.
5. **Only 9:16.** `layouts.ts` (B10) is the right shape; the design part is deciding which blocks
   survive in 4:5 and 1:1 — headline shrinks, the rail disappears, captions move to the lower third.

## 4. How to take part without stepping on the engine

- Brand packs are **data**: a design can ship one without touching Python or Remotion.
- Looks and captions are **Remotion components**: a design proposes frames (PNG mockups at the real
  size, with the real fonts) and the engine owner implements them.
- Caption text quality stays with **kaeasy** (`python lint.py --mode social --strict`); the v4 social
  card copy passes it as of this audit.
