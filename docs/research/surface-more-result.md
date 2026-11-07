# Surface-more: procedural lit materials (work in progress)

Lane `surface-more`, branch `claude/surface-more-b6cca1`, cut from `goal/lit-surfaces`.

## State

- Generator: `tools/surface_procedural.py` (numpy only; periodic spectral fBm, Worley, domain warp, reaction-diffusion,
  weave, scratches, thermal erosion). `python tools/build_surfaces.py --procedural` draws all of them.
- 20 candidate materials drawn at 384 px (budget: 13.26 MB of 15). Loops, critic and cuts: see below when finished.

## Done-when evidence

(filled in as each line is proven)

## Owner decisions

- N13: `news_check.imagery` reads only a story's `assets` ledger of pictures (stock, screenshots, AI). A surface plate is
  tone only and is never used for news, crime, incidents or deaths. Stricter reading kept: every procedural entry still
  carries `n13_label_required: true`; the owner may decide the „საილუსტრაციო“ label is not needed on pure grain.
