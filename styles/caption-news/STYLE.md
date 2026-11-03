# Caption News (`caption-news`)

> Fast social-feed news video built to be understood instantly with sound off, featuring heavyweight chunk captions and authoritative news cards.

## 1. At-a-Glance Signature
- Giant, high-contrast headline blocks and rapid subtitle cards timed directly to spoken speech.
- Strong grounding: solid dark canvas or documentary screenshot ground with official domain stamps (`matsne.gov.ge`, `gov.ge`).
- Accent underline or ink keyword block highlighting the single critical operative word per page (`tt_shorts.captions`).
- Prominent source pill and publication timestamp in header.

## 2. Vertical (1080×1920) Geometry & Safe Zones
- Header band ($y \in [0, 248]$): Source outlet chips, category tag, and date.
- Card/Stage Area ($y \in [248, 1380]$): Evidence card, document quote, or news statement.
- Captions Lower Third ($y \in [1380, 1552]$): Bold caption block. Spoken words in bright ink, waiting words in dimmed ink (`rgba(..., 0.42)`).
- Right margin clear zone ($x > 940$ below $y = 1100$) strictly preserved for social media UI overlays.

## 3. Georgian Mkhedruli Typography
- Heavy news headline weight: `FiraGO 700` or `FiraGO 900`.
- Word length adaptation: Georgian words average 7–9 characters (longer than English). Caption chunks are grouped in 2–4 words per line to prevent awkward wrapping.
- Quote scenes use proper Georgian quotation marks: „...“ (low-high quotation pair), never English quotes ("...").

## 4. Motion & Animation Rules
- Hard cuts and instant line snaps on voice pauses.
- Keyword wipe or accent reveal timed exactly to the settled frame of the keyword's spoken audio beat.
- Transitions: abrupt cut or authoritative horizontal wipe across the screen (10 frames).

## 5. Sound Craft
- Authoritative, driving news bed (politics, world, crime loops).
- Constant audio level from start to finish. Mix handles dialogue clarity in ffmpeg without Remotion ducking.
- SFX: solid documentary thud (`thud`) on major headline changes, light click (`click`) on source tag appearance.
