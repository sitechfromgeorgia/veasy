"""One story, every surface (ROADMAP D9 + B3): from one finished render, everything a publisher needs, with no new
voice and no model call.

  python -m tt_shorts.engine package <render.json> [--only srt,vtt,cover,carousel,teaser,texts,telegram]

It reads the render's manifest (<render>.json, written by `engine render`), the props Remotion drew it from
(<render>.props.json: word timings, the caption layout, scene frames, the pack) and the story, and writes
<render>-package/ beside the mp4 (store.package_dir):

  captions.srt, captions.vtt  the caption pages with the times the video shows them (props.captions)
  cover.png                   1080x1920: the hook at its most complete frame, without the captions
  carousel-01..0N.png         1080x1350 (4:5), 5-7 slides: the hook, the content scenes at their final frame, the
                              sources and the end card (QR, link, call to action); Remotion composition Slide
  teaser.mp4                  6-10 s: the hook and the last 3 s, cut from the mp4 by ffmpeg with a crossfade and
                              the audio faded in and out (no new frames, no new voice)
  texts.json                  YouTube title and description, Instagram, Facebook and TikTok captions
  telegram.md                 a post for the pack's Telegram channel (Telegram's Markdown: *bold*, [text](url))

Every text is code: the hook lines, the narration's sentences (checked with the story), the outlets, the date and
the pack's words and hashtags (brand.json "package"); each goes through ka_check's screen-text rules (links and
hashtags are left out of that check: they are Latin by nature). Links are meta.story_url with the platform as
utm_source, as the QR codes are.
"""
import json
import pathlib
import re
import shutil
import subprocess

from tt_shorts import brand, ka_check, meta, store

FPS = 30
PARTS = {
    "srt": "captions.srt: the caption pages with their exact times",
    "vtt": "captions.vtt: the same as WebVTT",
    "cover": "cover.png: 1080x1920, the hook at its most complete frame, no captions",
    "carousel": "carousel-01..0N.png: 5-7 slides at 1080x1350 (4:5) for Instagram and Facebook",
    "teaser": "teaser.mp4: 6-10 s, the hook and the last 3 s, cut from the mp4",
    "texts": "texts.json: YouTube title + description, Instagram, Facebook and TikTok captions",
    "telegram": "telegram.md: a post for the pack's Telegram channel",
}
EXIT = 7  # frames a scene takes to leave (remotion/src/NewsShort.tsx): the cover is the frame before
MIN_SLIDES, MAX_SLIDES = 5, 7
# remotion/src/Slide.tsx: the slide's scene box and its footer (tests/test_package.py checks they agree)
SLIDE_W, SLIDE_H = 1080, 1350
BOX_W, BOX_H, BOX_LEFT, BOX_TOP = 888, 964, 96, 196
BAND_TOP, BAND_BOTTOM, FOOTER_TOP = 152, 1204, 1228
INK_LEVEL = 90  # gray level above which a pixel is drawn ink or text, not the canvas, its motif or a 12% line
# (on a light theme, brand.json themes: below 255 - INK_LEVEL)
FITS = (1.0, 0.9, 0.8, 0.7)  # a slide's scale while it doesn't fit its box (Slide.tsx "fit")
TEASER = (6.0, 10.0)  # seconds
TAIL = 3.0  # the last seconds of the video in the teaser: the end card, its QR and the call to action
XFADE = 0.35  # the crossfade between the two parts
LIMITS = {"youtube_title": 100, "tiktok": 150, "youtube_description": 5000, "instagram": 2200}
SENTENCE_END = ".?!"


class PackageError(ValueError):
    pass


# ---------------------------------------------------------------- inputs


def load(render):
    """(manifest, props, story) of a render, from its .json manifest or its .mp4."""
    r = pathlib.Path(render)
    if r.name.endswith(".props.json"):
        manifest = r.with_name(r.name[:-len(".props.json")] + ".json")
    else:
        manifest = r if r.suffix == ".json" else r.with_suffix(".json")
    if not manifest.exists():
        raise PackageError(f"no render manifest {manifest} (engine render writes it beside the mp4)")
    m = json.loads(manifest.read_text(encoding="utf-8"))
    side = pathlib.Path(m.get("props") or store.props_path(manifest))
    if not side.exists():
        raise PackageError(f"{manifest.name} has no props file ({side.name}): it was rendered before `engine package` "
                           f"existed; render it again (the voice is cached, so it costs nothing)")
    story = pathlib.Path(m.get("story") or "")
    if not story.is_file():
        raise PackageError(f"the render's story {story} is gone")
    return ({**m, "_manifest": str(manifest)}, json.loads(side.read_text(encoding="utf-8")),
            json.loads(story.read_text(encoding="utf-8")))


def sentences(text):
    """The sentences of a Georgian text; a quote „…“ is never split, nor "tbilisi.today" or "1.5"."""
    out, cur, depth = [], "", 0
    for i, ch in enumerate(text):
        cur += ch
        if ch == "„":
            depth += 1
        elif ch in "“”" and depth:
            depth -= 1
        if ch in SENTENCE_END and depth == 0 and (i + 1 == len(text) or text[i + 1].isspace()):
            out.append(cur.strip())
            cur = ""
    if cur.strip():
        out.append(cur.strip())
    return out


def anchors(story):
    """Where each scene starts in the narration (a character index), from its "at" words with punctuation ignored
    (an anchor may leave out the narration's „quotes“); None for an anchor that isn't there."""
    text = story.get("narration", "")
    words = [(m.start(), ka_check.norm(m.group())) for m in re.finditer(r"\S+", text)]
    keys = [k for _, k in words]
    out, after = [], 0
    for s in story.get("scenes") or []:
        want = [k for k in (ka_check.norm(t) for t in str(s.get("at") or "").split()) if k]
        hit = next((i for i in range(after, len(keys) - len(want) + 1) if want and keys[i:i + len(want)] == want), None)
        out.append(words[hit][0] if hit is not None else None)
        after = hit + 1 if hit is not None else after
    return out


def body(story):
    """The narration's sentences before the outro (the sources and end scenes: "this story is covered by...",
    "subscribe"), which belong to the video, not to a post."""
    text = story.get("narration", "")
    cut = next((k for s, k in zip(story.get("scenes") or [], anchors(story))
                if s.get("type") in ("sources", "end") and k is not None), None)
    return sentences(text[:cut] if cut else text)


def headline(story):
    """The hook's lines as one line of text."""
    hook = next((s for s in story.get("scenes") or [] if s.get("type") == "hook"), {})
    return re.sub(r"\s+", " ", " ".join(hook.get("lines") or [])).strip().rstrip(".,:;")


def _restates(line, sentence):
    """The narration's first sentence usually says what the hook says: then a post skips it after the headline."""
    a = {ka_check.norm(w) for w in line.split()} - {""}
    b = {ka_check.norm(w) for w in sentence.split()}
    return bool(a) and len(a & b) >= 0.6 * len(a)


def clip(text, most):
    """At most `most` characters, cut at a word and without a dangling comma (no "…": K12)."""
    if len(text) <= most:
        return text
    cut = text[:most + 1].rsplit(" ", 1)[0] if " " in text[:most + 1] else text[:most]
    return cut.rstrip(" ,:;·")


def hashtags(story, b, most=5):
    """The category's own tag (its label, spaces dropped) and the pack's tags: 3-5, no repeats."""
    label = meta.category_label(story.get("category", ""), b)
    tags = ["#" + re.sub(r"[\s\-·.,:;!?]+", "", label)] + list(b["package"]["hashtags"])
    return list(dict.fromkeys(tags))[:most]


# ---------------------------------------------------------------- captions


def _ts(t, sep):
    ms = max(0, int(round(t * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def cues(cap):
    """[(start, end, text)]: one per caption page, its lines as the video shows them (seconds)."""
    out = []
    for p in (cap or {}).get("pages") or []:
        text = "\n".join(" ".join(w["text"] for w in cap["lines"][i]["words"]) for i in p["lines"])
        if p["end"] > p["start"] and text.strip():
            out.append((p["start"], p["end"], text))
    return out


def srt(cap):
    return "\n".join(f"{k}\n{_ts(a, ',')} --> {_ts(b, ',')}\n{t}\n" for k, (a, b, t) in enumerate(cues(cap), 1))


def vtt(cap):
    return "WEBVTT\n\n" + "\n".join(f"{_ts(a, '.')} --> {_ts(b, '.')}\n{t}\n" for a, b, t in cues(cap))


# ---------------------------------------------------------------- texts


LINK = re.compile(r"\[[^\]]*\]\([^)]*\)|https?://\S+")
TAG = re.compile(r"#[^\s#]+")


def text_problems(where, text, story):
    """ka_check's screen-text rules (K1 შენ, K12 no "!" or dashes, K19 no stray English, K14 quotes...) on one
    generated text. Links and hashtags are left out; quotes are compared with the narration they come from."""
    prose = TAG.sub(" ", LINK.sub(" ", text)).replace("*", "")
    pseudo = {"narration": "", "say": story.get("say") or {}, "scenes": [], "cta": prose}
    return [p.replace("cta", where, 1) for p in ka_check.problems(pseudo, {"text": story.get("narration", "")})]


def _escape_md(text):
    """Telegram's Markdown: _ * ` [ are markup outside a link."""
    return re.sub(r"([_*`\[])", r"\\\1", text)


def texts(story, b):
    """Every platform's text, by code -> {youtube, instagram, facebook, tiktok, telegram, hashtags, links}."""
    sid = story["id"]
    pk = b["package"]
    line = headline(story)
    sent = body(story)
    after = sent[1:] if sent and _restates(line, sent[0]) else sent  # what a post says after the headline
    outlets = meta.sources_line(story.get("sources") or [], shown=len(story.get("sources") or []), b=b)
    date = meta.ka_date(story["date"], b)["date"]
    tags = hashtags(story, b)
    links = {p: meta.story_url(sid, p, b) for p in ("youtube", "instagram", "facebook", "tiktok", "telegram")}

    def join(*parts):
        return "\n\n".join(p for p in parts if p)

    description = join(" ".join(sent), "\n".join(x for x in (outlets, date) if x),
                       pk["more"].format(url=links["youtube"]), " ".join(tags))
    lead = " ".join(after[:2])
    tiktok_tags = " ".join(tags[:3])
    telegram = join(f"*{_escape_md(line)}*", _escape_md(lead), _escape_md(outlets),
                    f"[{meta.display_url(sid, b)}]({links['telegram']})")
    return {
        "youtube": {"title": clip(line, LIMITS["youtube_title"]),
                    "description": clip(description, LIMITS["youtube_description"]),
                    "tags": [t.lstrip("#") for t in tags]},
        "instagram": {"caption": clip(join(line, lead, outlets, pk["link_in_bio"], " ".join(tags)), LIMITS["instagram"])},
        "facebook": {"caption": join(line, lead, outlets, pk["more"].format(url=links["facebook"]), " ".join(tags[:3])),
                     "link": links["facebook"]},
        "tiktok": {"caption": f"{clip(line, LIMITS['tiktok'] - len(tiktok_tags) - 1)} {tiktok_tags}"},
        "telegram": telegram,
        "hashtags": tags,
        "links": links,
    }


def texts_problems(t, story):
    """Limits and the Georgian screen rules on every generated text."""
    p = []
    if len(t["youtube"]["title"]) > LIMITS["youtube_title"]:
        p.append(f"youtube title: {len(t['youtube']['title'])} characters, at most {LIMITS['youtube_title']}")
    if len(t["tiktok"]["caption"]) > LIMITS["tiktok"]:
        p.append(f"tiktok caption: {len(t['tiktok']['caption'])} characters, at most {LIMITS['tiktok']}")
    if not 3 <= len(t["hashtags"]) <= 5:
        p.append(f"hashtags: {len(t['hashtags'])}, needs 3-5")
    for where, text in (("youtube.title", t["youtube"]["title"]), ("youtube.description", t["youtube"]["description"]),
                        ("instagram", t["instagram"]["caption"]), ("facebook", t["facebook"]["caption"]),
                        ("tiktok", t["tiktok"]["caption"]), ("telegram", t["telegram"])):
        p += text_problems(where, text, story)
    return p


# ---------------------------------------------------------------- carousel


def slide_plan(scenes, story, b):
    """The carousel's slides (render props scenes, each with the frame it is frozen at): the hook, up to 4 content
    scenes in the video's order, the sources and the end card. A story with too few scenes gets text slides of its
    narration sentences, so a carousel has 5-7 slides."""
    def frozen(s):
        return {**s, "freeze": max(0, int(s.get("duration", 1)) - 1)}
    hook = next(s for s in scenes if s["type"] == "hook")
    content = [s for s in scenes if s["type"] not in ("hook", "sources", "end")][:MAX_SLIDES - 3]
    src = next((s for s in scenes if s["type"] == "sources"), None) or \
        {"type": "sources", "from": 0, "duration": 90, "kicker": b["strings"]["source_many"]}
    end = next((s for s in scenes if s["type"] == "end"), None) or {"type": "end", "from": 0, "duration": 120}
    extra = []
    line = headline(story)
    sent = [x for x in body(story) if not _restates(line, x)]
    while len(content) + len(extra) + 3 < MIN_SLIDES and sent:
        take = sent[:2] if len(" ".join(sent[:2])) <= 200 else sent[:1]
        sent = sent[len(take):]
        extra.append({"type": "summary", "from": 0, "duration": 90, "text": " ".join(take),
                      "kicker": meta.category_label(story.get("category", ""), b)})
    return [frozen(s) for s in [hook, *extra, *content, src, end]]


def _gray(png):
    """A PNG as rows of 8-bit gray (through ffmpeg: no imaging library needed)."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.uint8).reshape(SLIDE_H, SLIDE_W)


def fit_problems(png, kind, light=False):
    """Anything drawn outside the slide's scene box: below it (above the footer) or right of it. A scene that does
    not fit overflows there (its body is centred, so it overflows up over its headline as much as down). light: the
    slide's theme is a light ground, so ink is the dark pixels."""
    g = _gray(png)
    if kind == "end":  # the end card has the whole band; nothing may reach the footer
        bands = {"over the footer": g[BAND_BOTTOM:FOOTER_TOP + 12, :]}
    else:
        bands = {"below its box": g[BOX_TOP + BOX_H + 4:FOOTER_TOP - 6, 24:SLIDE_W - 24],
                 "right of its box": g[BOX_TOP:BOX_TOP + BOX_H, BOX_LEFT + BOX_W + 8:SLIDE_W - 20]}
    return [f"{pathlib.Path(png).name} ({kind}): text or ink {where}, the scene doesn't fit the slide"
            for where, band in bands.items() if int(((band < 255 - INK_LEVEL) if light else (band > INK_LEVEL)).sum()) > 12]


# ---------------------------------------------------------------- teaser


def teaser_plan(props):
    """(cut, tail_from, seconds): the first part ends where the hook does (at a word boundary, inside the length
    window); the second part is the last ~3 s, starting at a word inside the end card."""
    fps = FPS
    scenes = props["scenes"]
    dur = props["durationInFrames"] / fps
    words = props.get("words") or []
    starts = [w["start"] for w in words]
    end_from = next((s["from"] / fps for s in scenes if s["type"] == "end"), dur - TAIL)
    near = [t for t in starts if dur - TAIL - 0.5 <= t <= dur - TAIL + 0.4 and t >= end_from]
    tail_from = min(near, key=lambda t: abs(t - (dur - TAIL))) if near else max(end_from, dur - TAIL)
    tail = dur - tail_from
    lo, hi = TEASER[0] - tail + XFADE + 0.05, TEASER[1] - tail + XFADE - 0.05
    hook_end = scenes[1]["from"] / fps if len(scenes) > 1 else dur
    if lo <= hook_end <= hi:
        cut = hook_end
    else:  # the boundary nearest the hook's end, after a sentence when there is one
        pairs = list(zip(words, words[1:]))
        sentence = [b["start"] for a, b in pairs if lo <= b["start"] <= hi and a["text"].rstrip("“”\"'").endswith(tuple(".?!:"))]
        anyword = [b["start"] for a, b in pairs if lo <= b["start"] <= hi]
        pool = sentence or anyword
        cut = min(pool, key=lambda t: abs(t - hook_end)) if pool else min(max(hook_end, lo), hi)
    cut = min(cut, tail_from - 0.5)
    return round(cut, 3), round(tail_from, 3), round(cut + tail - XFADE, 3)


def _has_audio(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                        str(mp4)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def cut_teaser(mp4, out, cut, tail_from):
    """[0, cut] and [tail_from, end] of the mp4, joined by a crossfade; the audio fades in and out at the ends."""
    total = cut + (seconds(mp4) - tail_from) - XFADE
    graph = [f"[0:v]split[va][vb]",
             f"[va]trim=end={cut:.3f},setpts=PTS-STARTPTS[v0]",
             f"[vb]trim=start={tail_from:.3f},setpts=PTS-STARTPTS[v1]",
             f"[v0][v1]xfade=transition=fade:duration={XFADE}:offset={cut - XFADE:.3f},format=yuv420p[v]"]
    maps = ["-map", "[v]"]
    if _has_audio(mp4):
        graph += [f"[0:a]asplit[aa][ab]",
                  f"[aa]atrim=end={cut:.3f},asetpts=PTS-STARTPTS[a0]",
                  f"[ab]atrim=start={tail_from:.3f},asetpts=PTS-STARTPTS[a1]",
                  f"[a0][a1]acrossfade=d={XFADE}:c1=tri:c2=tri,afade=t=in:d=0.15,"
                  f"afade=t=out:st={max(0.0, total - 0.6):.3f}:d=0.6[a]"]
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "160k", "-ar", "48000"]
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp4), "-filter_complex", ";".join(graph),
                    *maps, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
                    "-movflags", "+faststart", str(out)], check=True)
    return out


def seconds(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


# ---------------------------------------------------------------- remotion


def _public(work, b):
    """The pack's fonts and logo files where Remotion's staticFile() finds them (as props.build does)."""
    public = work / "public"
    shutil.rmtree(public, ignore_errors=True)
    (public / "fonts").mkdir(parents=True)
    for weight, f in b["_fonts"].items():
        shutil.copy(f, public / "fonts" / f"brand-{weight}.woff2")
    if b["_logo"]:
        (public / "brand").mkdir()
        for place, f in b["_logo"].items():
            shutil.copy(f, public / "brand" / f"{place}.svg")


def _remotion(args, work, data):
    from tt_shorts import props as render  # late: it pulls in the voice modules
    (work / "props.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    render._remotion(args, work)


def cover(props, work, out):
    """The hook at its most complete frame (the last before it leaves), without captions or sound."""
    hook = props["scenes"][0]
    frame = hook["from"] + max(0, hook["duration"] - EXIT - 1)
    data = {**props, "captions": None, "voice": None, "music": None}
    _remotion(["still", "src/index.ts", "NewsShort", str(out.resolve()), f"--frame={frame}"], work, data)
    return frame


def _slides(props, slides, b, work, out_dir, platform):
    """One Remotion render of the Slide composition, one PNG per slide -> [paths]; the QR tracks `platform`."""
    seq = work / "slides"
    shutil.rmtree(seq, ignore_errors=True)
    data = {**props, "captions": None, "voice": None, "music": None, "slides": slides, "durationInFrames": len(slides),
            "qrSvg": meta.qr_svg(meta.story_url(props["id"], platform, b), *brand.qr_colors(b["colors"]))}
    _remotion(["render", "src/index.ts", "Slide", str(seq.resolve()), "--sequence", "--image-format=png"], work, data)
    frames = sorted(seq.glob("*.png"), key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))
    paths = []
    for k, f in enumerate(frames, 1):
        target = out_dir / f"carousel-{k:02d}.png"
        shutil.move(str(f), target)
        paths.append(target)
    for old in out_dir.glob("carousel-*.png"):  # a re-run with fewer slides leaves none of the old ones
        if old not in paths:
            old.unlink()
    return paths


def carousel(props, slides, b, work, out_dir, platform="instagram"):
    """Render the slides; one that draws outside its box (fit_problems) is laid out taller and scaled down (FITS)
    and rendered again, at most len(FITS) - 1 times -> (paths, slides as drawn, problems left)."""
    slides = [dict(s) for s in slides]
    for attempt in range(len(FITS)):
        paths = _slides(props, slides, b, work, out_dir, platform)
        light = (props.get("brand") or {}).get("mode") == "light"
        found = [fit_problems(p, s["type"], light) for p, s in zip(paths, slides)]
        bad = [k for k, f in enumerate(found) if f and slides[k].get("fit", 1.0) > FITS[-1]]
        if not bad:
            break
        for k in bad:
            slides[k]["fit"] = next(f for f in FITS if f < slides[k].get("fit", 1.0))
    return paths, slides, [x for f in found for x in f]


# ---------------------------------------------------------------- the package


def make(render, only=None):
    """Write the render's package -> {"dir", "files", "problems", "warnings", ...}."""
    m, props, story = load(render)
    parts = list(PARTS) if not only else [x.strip() for x in only.split(",") if x.strip()]
    unknown = [x for x in parts if x not in PARTS]
    if unknown:
        raise PackageError(f"unknown parts {unknown}; known: {', '.join(PARTS)}")
    b = brand.themed(brand.load(props["brand"]["name"]), props.get("theme"))  # the render's theme: colors, logo
    out = store.package_dir(m["_manifest"])
    out.mkdir(parents=True, exist_ok=True)
    files, problems, info = {}, [], {}
    warnings = [f"preview render (engine {m['engine']}): this package is for review, not for publishing"] \
        if m.get("engine") in ("silent", "edge") else []
    cap = props.get("captions")
    if "srt" in parts:
        (out / "captions.srt").write_text(srt(cap), encoding="utf-8")
        files["srt"] = str(out / "captions.srt")
    if "vtt" in parts:
        (out / "captions.vtt").write_text(vtt(cap), encoding="utf-8")
        files["vtt"] = str(out / "captions.vtt")
    if ("srt" in parts or "vtt" in parts) and not cues(cap):
        problems.append("captions: the render has no caption pages")
    if "texts" in parts or "telegram" in parts:
        t = texts(story, b)
        problems += texts_problems(t, story)
        if "texts" in parts:
            (out / "texts.json").write_text(json.dumps({k: v for k, v in t.items() if k != "telegram"},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
            files["texts"] = str(out / "texts.json")
        if "telegram" in parts:
            (out / "telegram.md").write_text(t["telegram"] + "\n", encoding="utf-8")
            files["telegram"] = str(out / "telegram.md")
    work = None
    if "cover" in parts or "carousel" in parts:
        work = store.work_dir(f"package-{out.name}")
        _public(work, b)
    try:
        if "cover" in parts:
            try:
                info["cover_frame"] = cover(props, work, out / "cover.png")
                files["cover"] = str(out / "cover.png")
            except subprocess.CalledProcessError as e:
                problems.append(f"cover: remotion failed ({e.returncode})")
        if "carousel" in parts:
            slides = slide_plan(props["scenes"], story, b)
            info["slides"] = [s["type"] for s in slides]
            if not MIN_SLIDES <= len(slides) <= MAX_SLIDES:
                problems.append(f"carousel: {len(slides)} slides, needs {MIN_SLIDES}-{MAX_SLIDES}")
            try:
                pngs, drawn, left = carousel(props, slides, b, work, out)
                files["carousel"] = [str(p) for p in pngs]
                info["scaled"] = {p.name: s["fit"] for p, s in zip(pngs, drawn) if s.get("fit", 1.0) < 1}
                if len(pngs) != len(slides):
                    problems.append(f"carousel: {len(pngs)} images for {len(slides)} slides")
                problems += left
            except subprocess.CalledProcessError as e:
                problems.append(f"carousel: remotion failed ({e.returncode})")
    finally:
        if work:
            shutil.rmtree(work, ignore_errors=True)
    if "teaser" in parts:
        mp4 = pathlib.Path(m["file"])
        if not mp4.exists():
            problems.append(f"teaser: the render's mp4 {mp4} is gone")
        else:
            cut, tail_from, _ = teaser_plan(props)
            try:
                cut_teaser(mp4, out / "teaser.mp4", cut, tail_from)
                secs = seconds(out / "teaser.mp4")
                info["teaser"] = {"seconds": round(secs, 2), "hook_until": cut, "tail_from": tail_from}
                files["teaser"] = str(out / "teaser.mp4")
                if not TEASER[0] - 0.1 <= secs <= TEASER[1] + 0.1:
                    problems.append(f"teaser: {secs:.1f}s, needs {TEASER[0]:.0f}-{TEASER[1]:.0f}s")
            except subprocess.CalledProcessError as e:
                problems.append(f"teaser: ffmpeg failed ({e.returncode})")
    store.log("packaged", render=m["_manifest"], parts=parts, problems=problems)
    return {"dir": str(out.resolve()), "render": m["_manifest"], "files": files, **info, "problems": problems,
            "warnings": warnings}
