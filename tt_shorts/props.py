"""Story JSON -> Remotion render props -> mp4 (remotion/, composition NewsShort).

The writer's story JSON gives the text; this adds what comes from data and code: the voice and its word timings
(speech.py), scene start frames, the date in the brand's time zone, the sources, the QR code, the music loop and the
call to action (meta.py), the brand pack itself (brand.py: colors, words, logo; its fonts and logo files are
copied into the render's public dir), the scenes' pictures (assets.py: the ledger's local files, copied into
public/media/, with their label and credit) and the sound effects' cues (sfx.py, format key sfx). Then it runs
`remotion render` and mixes the sound with ffmpeg (voice, music and the effects, each at one level).

  python -m tt_shorts.props stories/24835.json --variant editorial       # preview voice (edge-tts ka-GE)
  python -m tt_shorts.props stories/24835.json --variant kinetic --voice gemini --tone anchor
  python -m tt_shorts.props stories/24835.json --variant cards --voice silent
  python -m tt_shorts.props stories/24835.json --still 120,400            # PNG frames instead of a video
"""
import argparse
import glob
import json
import os
import pathlib
import shutil
import subprocess

from tt_shorts import (art, assets, beats as beat_track, brand, captions, chapters as chapters_of, directors,
                       geo, icons, meta, rubrics, sfx as effects, speech, store, swipe, variety, voices)

ROOT = speech.ROOT
REMOTION = ROOT / "remotion"
FPS = speech.FPS
VARIANTS = brand.LOOKS
NOTES = {"edge": "preview_edge", "silent": "preview_silent"}  # the pack's words for a preview render


CAPTIONS = os.environ.get("SHORTS_CAPTIONS", "page")  # page | roll (captions.py)


TRANSITIONS = ("cut", "line", "panel", "wipe", "slide", "push", "dot", "meter", "fade", "shutter", "split", "corner", "iris", "blind")
DEFAULT_TRANSITION = {"editorial": "line", "cards": "line", "kinetic": "panel"}


def transition_for(name, variant):
    """The cut between scenes: a format's choice, or the look's own ("auto")."""
    return DEFAULT_TRANSITION[variant] if name in (None, "auto") else name


def _scene(s, a, b, mark=None, media=None):
    """One scene's props: its frames, a drawing as a safe tree instead of the writer's SVG, its voice-synced mark
    (speech.mark_frames: where, when and how the "em" phrase is drawn over; marks.py) and its picture (assets.py:
    the local file, the label and the credit, instead of the ledger reference)."""
    out = {**s, "from": a, "duration": b - a}
    out.pop("media", None)
    out.pop("show", None)
    if s.get("media") and media and s["media"].get("asset") in media:
        out["media"] = media[s["media"]["asset"]]
    if s.get("type") == "draw":
        out["art"] = art.sanitize(s.get("svg", ""))[0]
        out.pop("svg", None)
    if mark:
        out["mark"] = mark
    return out


def loops_for(music, family):
    """The music loops a video can use: the family's (or the named family's), none when music is off."""
    if music == "off" or os.environ.get("SHORTS_MUSIC", "on").lower() in ("off", "0", "no"):
        return []
    fam = family if music in (None, "family") else music
    return sorted(speech.MUSIC_DIR.glob(f"{fam}-*.m4a")) or sorted(speech.MUSIC_DIR.glob("society-*.m4a"))


def theme_for(story, theme="default", director=None):
    """The theme a video is drawn in: "default" (or None) the pack's default theme; a name, that theme of the pack
    (an unknown one fails); "auto", the least used lately among the pack's allowed themes, inside the director's
    "themes" when it names some (variety.pick_theme; a re-render keeps its theme)."""
    b = brand.of(story)
    if theme in (None, "", "default"):
        return b["default_theme"]
    if theme != "auto":
        return brand.themed(b, theme)["theme"]
    pool = brand.theme_names(b, allowed_only=True)
    return variety.pick_theme(b["name"], story["id"], pool, (director or {}).get("themes"))


def choose(story, variant, transition="auto", music="family", director=None, style=None, outro=swipe.DEFAULT_OUTRO):
    """The variety picks of one video in one look -> (style {hook, motif, enter, transition, music}, the director dict
    or None, the music loops, the story's main icon, the novelty guard's report). Reads the variety history and
    records nothing (render_story does, after a render), so `engine plan` can show the picks for free. The picks
    pass the novelty guard (variety.choose): a plan too close to one of the brand's recent videos is re-rolled here,
    before any voice. director: an id instead of the story's own; style: picks to force (then the report measures
    them, without a re-roll); outro: which scenes are shown (part of the fingerprint)."""
    b = brand.of(story)
    loops = loops_for(music, meta.family(story.get("category", ""), b))
    main = icons.story_icon(story)  # the story's main icon: the "icons" motif is possible only with one
    did = director or story.get("director")
    chosen = directors.get(did) if did else None  # an unknown director fails before anything renders
    seq = [s["type"] for s in swipe.shown_scenes(story, outro)]
    picked, novelty = variety.choose(b["name"], story["id"], variant, transition, loops, icon=bool(main),
                                     director=chosen, scenes=seq)
    st = {**picked, **(style or {})}
    if style:  # a forced style (the goldens): report what is drawn, not what was picked
        novelty = variety.assess(b["name"], story["id"], {**st, "director": chosen["id"] if chosen else None}, seq)
    return st, chosen, loops, main, novelty


def build(story_path, variant="auto", engine="edge", tone=None, edge_voice=speech.EDGE_VOICES["eka"], platform="shorts",
          caption_design=None, music="family", transition="auto", style=None, outro=swipe.DEFAULT_OUTRO, director=None,
          sfx="off", theme="default", beats="on",
          chapters="off"):
    """Story -> (work dir, Remotion props). music: "family" (by category), a family name, or "off".
    transition: "auto" (variety picks one that suits the look) or one of TRANSITIONS.
    style: {hook, motif, enter, transition, music} to force; by default variety.choose() picks the least used, and its
    novelty guard re-rolls a plan too close to a recent video, all before the voice is made (props "novelty").
    outro: card | overlay | loop (swipe.py: the end card, a chip over the last scene, or a seamless loop).
    director: a directors.py id to use instead of the story's own "director" (render --director); with one, the
    variety picks stay inside its subsets and props.style carries its motion numbers and current.
    sfx: off | on (format key): the sound effects' cues from the timeline (sfx.py), mixed by mix_audio.
    theme: "default" (the pack's), "auto" (variety picks among the pack's allowed themes) or a theme's name
    (theme_for); props.brand carries that theme's colors, props.theme its name, and its logo files are copied.
    beats: on | off (beats.py: a change inside each scene every 1.5-3 s, on the words); chapters: auto | on | off
    (chapters.py: the "01 / 03" bar; auto: for a video of chapters.AUTO_SECONDS or more)."""
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    story = brand.with_say(story)  # the pack's own names (SiTech -> საი-თეჩი) are spoken right
    sid = story["id"]
    b = brand.of(story)
    category = story.get("category", "")
    did = director or story.get("director")
    b = brand.themed(b, theme_for(story, theme, directors.get(did) if did else None))
    if variant == "auto":  # the look follows the kind of story (the pack's look_by_family)
        variant = meta.variant_for(category, b)
    design = caption_design or CAPTIONS
    work = store.work_dir(f"{b['name']}-{sid}-{variant}-{design}-{engine}"
                          + ("" if b["theme"] == b["default_theme"] else f"-{b['theme']}"))
    key = speech.voice_key(story, engine, tone, edge_voice)
    voice_dir = store.voice_dir(key) if key else work  # one cached track per voice + text: other looks cost no TTS
    public = work / "public"
    shutil.rmtree(public, ignore_errors=True)
    (public / "fonts").mkdir(parents=True)
    for weight, f in b["_fonts"].items():  # the pack's one family; stable names for staticFile() (remotion/src/Root.tsx)
        shutil.copy(f, public / "fonts" / f"brand-{weight}.woff2")
    if b["_logo"]:
        (public / "brand").mkdir()
        for place, f in b["_logo"].items():
            shutil.copy(f, public / "brand" / f"{place}.svg")

    # the picks and the novelty guard come before the voice: a plan too close to a recent video is re-rolled
    # first (choose -> variety.choose)
    st, chosen, loops, main, novelty = choose(story, variant, transition, music, director, style, outro)

    media = assets.for_props(story, b, public, FPS)  # the ledger's files (fetched again, checked, if gc took them)
    audio, words = speech.voice(story, voice_dir, engine, tone, edge_voice)
    trim = swipe.lead_trim(words, swipe.leading_silence(audio)) if audio else 0.0  # the voice starts at once
    words = swipe.shift(words, trim)  # mix_audio cuts the same seconds from the track
    shown, marks, chip = swipe.plan(story, words, outro)
    bed = next((f for f in loops if f.name == st["music"]), loops[0] if loops else None)
    for f in (audio, bed):
        if f:
            shutil.copy(f, public / f.name)
    d = meta.ka_date(story["date"], b)
    link_shown, opens = meta.links(story, platform, b)  # the pack's story page, or the source's own (a law's article)
    props = {
        "brand": brand.for_remotion(b),
        "theme": b["theme"],  # the pack's theme the video is drawn in (brand.themed): its colors are props.brand's
        "variant": variant, "id": sid, "category": meta.category_label(category, b),
        "date": {k: d[k] for k in ("date", "time", "weekday")},
        "when": meta.when(d, b),
        "sources": story.get("sources", []), "sourcesLine": meta.sources_line(story.get("sources", []), b=b),
        "cta": story.get("cta") or meta.cta_for(sid, b),
        "url": (story.get("url") or "").replace("https://", "").rstrip("/") or link_shown,
        "qrSvg": meta.qr_svg(story.get("url") or opens, *brand.qr_colors(b["colors"])),
        "durationInFrames": marks[-1],
        "transition": st["transition"] if st["transition"] in TRANSITIONS else transition_for(transition, variant),
        "style": {**{k: st[k] for k in variety.OPTIONS}, **(directors.style(chosen) if chosen else {})},
        "novelty": novelty,  # the guard's report (variety.choose): the nearest recent video, re-rolls, a warning
        "outro": outro, "outroFrom": chip,  # the frame the outro chip comes in (None: the end card)
        "scenes": icons.attach([_scene(s, a, z, m, media) for s, a, z, m in zip(
            shown, marks, marks[1:], speech.mark_frames(shown, words, marks, sid, meta.family(category, b)))], story),
        "motifIcon": icons.nodes(main) if st["motif"] == "icons" else None,  # the icon tiled in the background
        "words": words,
        "captions": None,  # below, once the scenes are built (keyword captions read their em phrases and names)
        "voice": audio.name if audio else None, "voiceVolume": 1.0, "voiceTrim": trim,
        "music": bed.name if bed else None, "musicVolume": 0.5 if engine == "silent" else 0.22,
        "previewNote": b["strings"][NOTES[engine]] if engine in NOTES else None,
        "rubric": rubrics.chip(story),  # the hook's chip „დღის ციფრი · #12“ (rubrics.py), code's text
        # words the aligner barely heard: the voice may have skipped or changed them (speech.voice_qa; Gemini only)
        "voiceQa": story.get("qa", {}).get("voice", []),
    }
    geo.attach(props["scenes"], meta.family(category, b))  # a Georgian place: only what its map scene draws
    props["captions"] = captions.layout(words, design, end=marks[-1] / FPS, font=b["_fonts"]["700"],
                                        keys=captions.candidates(props["scenes"], FPS) if design == "keyword" else None,
                                        style=brand.keyword_style(b))
    if beats != "off":  # a visible change every 1.5-3 s inside each scene, landed on the words (beats.py)
        beat_track.attach(props["scenes"], words)
    props["chapters"] = chapters_of.split(props["scenes"], marks[-1], chapters)  # "01 / 03" (chapters.py), or None
    props["sfx"] = effects.cues({**props, "scenario": story.get("scenario")}) if sfx == "on" else []  # the accents' times (sfx.py); ffmpeg mixes them
    (work / "props.json").write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    return work, props


def chrome():
    """A chrome-headless-shell for Remotion: SHORTS_CHROMIUM, else Playwright's, else Remotion downloads its own."""
    if os.environ.get("SHORTS_CHROMIUM"):
        return os.environ["SHORTS_CHROMIUM"]
    found = sorted(glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell") +
                   glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))
    return found[-1] if found else None


def _remotion(args, work):
    npx = shutil.which("npx") or "npx"  # npx.cmd on Windows, which a bare "npx" can't start
    cmd = [npx, "remotion", *args, f"--props={work / 'props.json'}", f"--public-dir={work / 'public'}", "--log=error"]
    if chrome():
        cmd.append(f"--browser-executable={chrome()}")
    subprocess.run(cmd, cwd=REMOTION, check=True)


MUSIC_DB = -13.0  # the bed under the voice: one constant level, ~13 LU below the -16 LUFS voice (no ducking)
MUSIC_DB_SILENT = -1.0  # a preview without a voice: the music is the sound (about -17 LUFS)


def mix_audio(work, props, video, out):
    """Picture from Remotion + voice + music + sound effects, mixed by ffmpeg. The voice is levelled on its own; the
    music sits at one constant level with a fade in and out, so nothing rises and falls under the speech (the
    owner's ear, 2026-11-01: the ducked bed pumped). The voice's leading silence beyond swipe.LEAD_KEEP is cut
    (props "voiceTrim"; the word timings were moved by build()); a loop keeps the music level to the last frame.
    The effects (props "sfx": [{t, name}], sfx.py) are one track at one constant level (sfx.LEVEL_DB): no ducking,
    no risers. Engine-free: any engine's picture gets the same sound from the same props."""
    dur = props["durationInFrames"] / FPS
    public = work / "public"
    inputs, graph, mix = ["-i", str(video)], [], []
    if props["voice"]:
        inputs += ["-i", str(public / props["voice"])]
        trim = props.get("voiceTrim") or 0
        cut = f"atrim=start={trim:.3f},asetpts=PTS-STARTPTS," if trim else ""
        graph.append(f"[1:a]{cut}aresample=48000,loudnorm=I=-16:TP=-2:LRA=7,aformat=channel_layouts=stereo,"
                     f"apad,atrim=0:{dur:.3f}[voice]")
        mix.append("[voice]")
    if props["music"]:
        k = len(inputs) // 2
        inputs += ["-stream_loop", "-1", "-i", str(public / props["music"])]
        db = MUSIC_DB if props["voice"] else MUSIC_DB_SILENT
        fade_in, fade_out = swipe.music_fades(props.get("outro"))
        graph.append(f"[{k}:a]aresample=48000,atrim=0:{dur:.3f},volume={db}dB,afade=t=in:d={fade_in},"
                     f"afade=t=out:st={max(0, dur - fade_out):.3f}:d={fade_out}[bed]")
        mix.append("[bed]")
    if props.get("sfx"):
        k = inputs.count("-i")  # the music's -stream_loop makes len(inputs) // 2 wrong after it
        track = effects.track(props["sfx"], dur, work / "sfx.wav")
        inputs += ["-i", str(track)]
        graph.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.3f},"
                     f"volume={effects.LEVEL_DB}dB[sfx]")
        mix.append("[sfx]")
    if not mix:
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-c", "copy", str(out)], check=True)
        return out
    graph.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,alimiter=limit=0.89:level=disabled[a]")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(graph),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{dur:.3f}", "-movflags", "+faststart", str(out)], check=True)
    return out


def render_video(work, props, out):
    out = pathlib.Path(out).resolve()
    raw = work / "raw.mp4"
    _remotion(["render", "src/index.ts", "NewsShort", str(raw), "--muted", f"--concurrency={speech.workers()}"], work)
    out.parent.mkdir(parents=True, exist_ok=True)
    mix_audio(work, props, raw, out)
    raw.unlink()
    return out


def render_stills(work, frames, out_dir):
    out_dir = pathlib.Path(out_dir).resolve()  # remotion runs in remotion/: a relative path would land there
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in frames:
        png = out_dir / f"{work.name}-{f}.png"
        _remotion(["still", "src/index.ts", "NewsShort", str(png), f"--frame={f}"], work)
        paths.append(png)
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--variant", default="auto", choices=("auto",) + VARIANTS, help="auto: by the story's category")
    ap.add_argument("--voice", default="edge", choices=["edge", "gemini", "silent"])
    ap.add_argument("--tone", help=f"gemini preset: {', '.join(voices.PRESETS)}")
    ap.add_argument("--edge-voice", default="eka", choices=list(speech.EDGE_VOICES))
    ap.add_argument("--captions", choices=list(captions.DESIGNS), help="caption design (default SHORTS_CAPTIONS or page)")
    ap.add_argument("--outro", default=swipe.DEFAULT_OUTRO, choices=swipe.OUTROS, help="end card, chip overlay or loop")
    ap.add_argument("--still", help="comma-separated frame numbers: PNG stills instead of the video")
    ap.add_argument("--out", default=str(ROOT / "out"))
    a = ap.parse_args()
    work, props = build(a.story, a.variant, a.voice, a.tone, speech.EDGE_VOICES[a.edge_voice], caption_design=a.captions,
                        outro=a.outro)
    if a.still:
        for p in render_stills(work, [int(x) for x in a.still.split(",")], pathlib.Path(a.out) / "stills"):
            print(p)
    else:
        name = f"{props['id']}-{props['variant']}" + ("" if a.voice == "gemini" else f"-{a.voice}") + (f"-{a.captions}" if a.captions else "")
        out = render_video(work, props, pathlib.Path(a.out) / f"{name}.mp4")
        print(f"{out} | {props['durationInFrames'] / FPS:.1f}s | {len(props['scenes'])} scenes | music {props['music']}")
