---
name: package
description: "Use after a Veasy video has rendered and passed QA, when it should go out on more than YouTube Shorts: subtitles, a cover, an Instagram/Facebook carousel, a short teaser, platform titles and captions, a Telegram post, all from the one render with no new voice and no model call. Examples: \"package 24725 for every platform\", \"make the carousel and the Facebook text of this video\", \"I need SRT subtitles for this Short\""
---

# One story, every surface

From one finished render, `engine package` makes what each platform needs. It costs nothing: no TTS, no model
call. Everything comes from the render's own files (its timings, caption pages, scenes and brand pack) and the
story. Most Georgians who get news on social media use Facebook; carousels do well on Instagram; every platform
gets its own text.

```bash
python -m tt_shorts.engine package <render>.json                       # everything (about 15-30 s)
python -m tt_shorts.engine package <render>.json --only texts,telegram   # just the texts (instant)
```
Tool: `veasy_package` (`render`, `only`). `<render>.json` is the manifest `engine render` writes beside the mp4
(`renders/<brand>/<day>/<ref>-<format>-<look>-<captions>.json` under VEASY_HOME; a queue job's `result.file` with
`.json`). The mp4's path works too. A render made before the package existed has no `.props.json`: render it again
(the voice is cached, so that is free).

## What it writes: `<render>-package/` beside the mp4

| File | For | What |
|---|---|---|
| `captions.srt`, `captions.vtt` | YouTube, Facebook, accessibility | the video's caption pages with their exact times |
| `cover.png` | thumbnail, reel cover | 1080x1920, the hook at its most complete frame, no captions |
| `carousel-01..0N.png` | Instagram, Facebook (also a Telegram album) | 1080x1350 (4:5), 5-7 slides: hook, up to 4 content scenes, sources, end card with the QR (utm_source=instagram), link and call to action |
| `teaser.mp4` | stories, a second post | 6-10 s: the hook, a crossfade, the last ~3 s (the end card); audio faded in and out |
| `texts.json` | every platform | `youtube.title` (≤100), `youtube.description` (narration, outlets, date, link with utm_source=youtube, hashtags), `instagram.caption` (link in bio), `facebook.caption` + `link`, `tiktok.caption` (≤150), `hashtags`, `links` per platform |
| `telegram.md` | the pack's Telegram channel | headline, 1-2 narration sentences, the outlets, the link (Telegram's legacy Markdown: send with parse_mode `Markdown`) |

The JSON result lists the files, the slides (`slides`), any slide scaled to fit (`scaled`), the cover's frame and
the teaser's cut. `problems` must be empty; `warnings` says when the render was a preview (`--engine silent` or
`edge`): such a package is for review, never for publishing.

## The rules it keeps (don't work around them)

- **Texts are code, not a writer:** the hook lines, the narration's sentences (already checked with the story),
  the outlets, the date and the pack's words (`brand.json` `package`: the link line, "link in bio", hashtags). The
  video's outro ("covered by N outlets", "subscribe") stays out of the posts. Each text passes `ka_check`'s screen
  rules: შენ not თქვენ (K1), no "!", "…" or long dashes (K12), no stray English (K19); a problem names the text
  (`youtube.title`, `facebook`...). Fix the story or the pack, not the text by hand.
- **Hashtags:** the category's own (its label) first, then the pack's; 3-5. A new client's tags go in its pack's
  `package.hashtags` (`veasy:brands`).
- **Carousel layout:** each slide is the scene's own component at its final frame, in the pack and the video's look.
  A slide is checked pixel by pixel for anything drawn outside its box; one that doesn't fit is laid out taller and
  scaled down (to 0.9, 0.8, 0.7). A problem left after that is a story problem (too much text in that scene).
- **Look at it** before posting: open `cover.png` and every `carousel-*.png` (nothing clipped, the accent only on
  dots and the button, the source and the link visible), and play `teaser.mp4` once.

Publishing itself (uploading to YouTube, Meta, TikTok, Telegram) is not part of Veasy yet; hand the folder to
whoever posts.
