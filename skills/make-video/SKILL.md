---
name: make-video
description: "The single front door to Veasy. Use when asked to create, plan, or render any video from a sentence, story, article, or document. You name at most a brand and a style, answer one round of questions, and get a finished checked film."
---

# Make a video with Veasy

Veasy has one front door for any person or AI: **one sentence request**, at most a **brand** and a **style**, **one round of questions** for what code cannot decide, and a finished, checked vertical video (1080×1920, Georgian voice, captions, music, mix).

All existing expert commands and flags keep working underneath.

```bash
python -m tt_shorts.engine make "<request>" [--brand <brand>] [--style <style>] [--source <src>] [--length <len>]
```
Or tool `veasy_make({"request": "...", "brand": "...", "style": "..."})`.

---

## 1. The three concepts

A newcomer only meets three things:

| Concept | What it is | Choices & Defaults |
|---|---|---|
| **brand** | Who the video is for | `tbilisi-today` (default), `sitech`, or custom pack. See `veasy:brands`. |
| **style** | How it looks and sounds | 18 named film styles (`swiss-motion`, `living-screencast`, `countdown`...). Omit to let variety pick. See `veasy:styles`. |
| **story** | What the video is about | Your sentence request, article, document, or story JSON. |

### Visual Catalogue
Browse the full visual library before choosing:
```bash
python -m tt_shorts.engine gallery           # builds out/gallery.html with stills & clips of all 18 styles, 3 looks, 31 scene brushes, 8 directors
python -m tt_shorts.engine options           # leads with brands & styles (with stills); advanced options under "advanced"
```

---

## 2. What code decides automatically

You don't need to specify formats, engines, looks, or directors. From your sentence, code derives:

1. **Story & Program**: the facts come only from what the request points at, never from its words:
   - a story file or a story's name in `stories/` (`stories/24835.json`, `bipi-draws`) → that story;
   - a source ref → the writer writes it first (as `engine write`), and the program comes from the source:
     a bare number is a cluster id (`news`), a URL is `url` (`explainer`), `--source ordo` + `constitution:17` is
     `law`, `--source sitech` + a post is `blog`. The ref is the last word of the request.
   - a sentence with neither → `needs_input`, even with `--yes`. Answer with the source and call again.
   See `veasy:programs` for details.
2. **Style**: if `--style` is omitted, `variety.pick_style` chooses the least-used style permitted for that brand and program.
3. **Engine**: Remotion for high-volume data/news brushes; HyperFrames for composed fiction/fables. See `veasy:compose`.
4. **Director, Look & Theme**: picked from the style's invariants (`picks.directors`, `picks.looks`) and brand theme. See `veasy:directors`.
5. **Format & Duration**: default format for the program, scaled to target length (`short` 15-30s, `standard` 30-45s, `long` 45-60s). See `veasy:formats`.

---

## 3. The ONE round of questions

Before rendering, Veasy asks **ONE single round of questions** strictly for what code cannot decide on its own:

1. **Facts / Source**: asked *only* if your request names no story file, story name, URL or source ref.
2. **Custom Assets**: whether you wish to include custom logos or images (default: no; see `veasy:media`).
3. **Storyboard Preview**: whether to inspect the contact sheet first (`--preview-storyboard`) or render immediately.

### Automation & Non-interactive Flags
- `--yes` (`-y`): skips questions, accepts code defaults, renders immediately. It never invents the facts: without a
  source the answer is still `needs_input`.
- `--preview-storyboard`: stops after `engine plan` and returns contact sheet stills (`.plan.jpg`).
- `--queue`: adds the job to Veasy's job queue instead of rendering in-process. See `veasy:queue`.
- `--engine silent`: free preview voice (no paid TTS API).

---

## 4. Examples

### A news cluster (default brand): the writer writes it, then it renders
```bash
python -m tt_shorts.engine make "24835" --yes
```

### A story that is already written, in a named style
```bash
python -m tt_shorts.engine make "stories/explainer-inflation.json" --style swiss-motion --yes
```

### Georgian law: article 17 of the Constitution
```bash
python -m tt_shorts.engine make "კონსტიტუციის მე-17 მუხლი constitution:17" --source ordo --yes
```

### Composed story for children (HyperFrames)
```bash
python -m tt_shorts.engine make "bipi-draws" --brand sitech --yes
```

---

## 5. When to use specialized skills

`veasy:make-video` is the only skill you need to start. Route to others only when a specific expert step is required:

- **Style details**: read `veasy:styles` for style invariants, sound palettes, plucking models, and `TEXTS(t)`.
- **Brand pack creation / WCAG**: read `veasy:brands` to create `brands/<name>/` from guidelines with `engine brand new`.
- **Custom story scripts**: read `veasy:write-script` to hand-author scenes or repair text fields.
- **Rubrics & Chips**: read `veasy:rubrics` for „დღის ციფრი“, „რა იცვლება“, „ამბავი გრძელდება“.
- **Composed HyperFrames engineering**: read `veasy:compose` for blocks, timeline assembly, and Playwright DOM checks.
- **Batch publishing & Queues**: read `veasy:queue` for background workers, retries, and daily runs.
- **Visual QA & ASR**: read `veasy:qa` for the layout probe, safe zone audits, and wav2vec2 speech checks.
- **Multi-platform publishing**: read `veasy:package` for `.srt`, covers, 4:5 carousels, teasers, and Telegram posts.
- **Media licenses**: read `veasy:media` for official screenshots and illustrative images (news rule N13).
- **Directed pacing**: read `veasy:directors` for pacing, hook, and motif constraints.
- **Show formats**: read `veasy:formats` for show formats (news, explainer, showcase, story, number, digest).

---

## Hard Rules

- **Brand pack is law**: dark canvas, light ink, 1 accent that is never on text, 1 font family, safe zone strictly respected (scene text ends at y=1380, captions at y=1552).
- **News integrity**: news rules N1-N5 never get relaxed; numbers and quotes must match sources verbatim.
- **No paid API in preview**: use `engine plan`, `still`, `probe`, and `--engine silent` / `edge`.
