"""Story JSON -> Remotion render props -> mp4 (video/remotion, composition NewsShort).

The writer's story JSON gives the text; this adds what comes from data and code: the voice and its word timings
(speech.py), scene start frames, the date in Tbilisi time, the sources, the QR code, the music loop and the call to
action (meta.py). Then it runs `remotion render` and levels the loudness with ffmpeg.

  python -m tt_shorts.props stories/24835.json --variant editorial       # preview voice (edge-tts ka-GE)
  python -m tt_shorts.props stories/24835.json --variant kinetic --voice gemini --tone anchor
  python -m tt_shorts.props stories/24835.json --variant cards --voice silent
  python -m tt_shorts.props stories/24835.json --still 120,400            # PNG frames instead of a video
"""
import argparse
import datetime as dt
import glob
import json
import os
import pathlib
import shutil
import subprocess

from tt_shorts import meta, speech, voices

ROOT = speech.ROOT
REMOTION = ROOT / "remotion"
FPS = speech.FPS
VARIANTS = ("editorial", "kinetic", "cards")
NOTES = {"edge": "დროებითი ხმა · პრევიუ", "silent": "ხმის გარეშე · პრევიუ"}


def build(story_path, variant, engine="edge", tone=None, edge_voice=speech.EDGE_VOICES["eka"], platform="shorts"):
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    sid = story["id"]
    work = ROOT / "work" / f"{sid}-{variant}-{engine}"
    public = work / "public"
    shutil.rmtree(public, ignore_errors=True)
    (public / "fonts").mkdir(parents=True)
    for f in (ROOT / "assets" / "fonts").glob("firago-*.woff2"):  # one family (brand v1.2); stable names for staticFile()
        shutil.copy(f, public / "fonts" / f"firago-{f.name.split('-')[1].split('.')[0]}.woff2")

    audio, words = speech.voice(story, work, engine, tone, edge_voice)
    marks = speech.scene_frames(story, words)
    category = story.get("category", "society")
    music = speech.music_for(sid, category)
    for f in (audio, music):
        if f:
            shutil.copy(f, public / f.name)
    d = meta.ka_date(story["date"])
    props = {
        "variant": variant, "id": sid, "category": meta.category_label(category),
        "date": {k: d[k] for k in ("date", "time", "weekday")},
        "when": "დღეს" if d["day"] == dt.datetime.now(meta.TBILISI).date() else d["date"],
        "sources": story.get("sources", []), "sourcesLine": meta.sources_line(story.get("sources", [])),
        "cta": story.get("cta") or meta.cta_for(sid),
        "url": f"tbilisi.today/stories/{sid}", "qrSvg": meta.qr_svg(meta.story_url(sid, platform)),
        "durationInFrames": marks[-1],
        "scenes": [{**s, "from": a, "duration": b - a} for s, a, b in zip(story["scenes"], marks, marks[1:])],
        "words": words,
        "voice": audio.name if audio else None, "voiceVolume": 1.0,
        "music": music.name if music else None, "musicVolume": 0.5 if engine == "silent" else 0.22,
        "previewNote": NOTES.get(engine),
    }
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
    cmd = ["npx", "remotion", *args, f"--props={work / 'props.json'}", f"--public-dir={work / 'public'}", "--log=error"]
    if chrome():
        cmd.append(f"--browser-executable={chrome()}")
    subprocess.run(cmd, cwd=REMOTION, check=True)


MUSIC_DB = -13.0  # the bed under the voice: one constant level, ~13 LU below the -16 LUFS voice (no ducking)
MUSIC_DB_SILENT = -6.0  # a preview without a voice: the music is the sound


def mix_audio(work, props, video, out):
    """Picture from Remotion + voice + music, mixed by ffmpeg. The voice is levelled on its own; the music sits at
    one constant level with a fade in and out, so nothing rises and falls under the speech (the owner's ear,
    2026-11-01: the ducked bed pumped)."""
    dur = props["durationInFrames"] / FPS
    public = work / "public"
    inputs, graph, mix = ["-i", str(video)], [], []
    if props["voice"]:
        inputs += ["-i", str(public / props["voice"])]
        graph.append("[1:a]aresample=48000,loudnorm=I=-16:TP=-2:LRA=7,aformat=channel_layouts=stereo,"
                     f"apad,atrim=0:{dur:.3f}[voice]")
        mix.append("[voice]")
    if props["music"]:
        k = len(inputs) // 2
        inputs += ["-stream_loop", "-1", "-i", str(public / props["music"])]
        db = MUSIC_DB if props["voice"] else MUSIC_DB_SILENT
        graph.append(f"[{k}:a]aresample=48000,atrim=0:{dur:.3f},volume={db}dB,afade=t=in:d=1.2,"
                     f"afade=t=out:st={max(0, dur - 2.5):.3f}:d=2.5[bed]")
        mix.append("[bed]")
    if not mix:
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-c", "copy", str(out)], check=True)
        return out
    graph.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,alimiter=limit=0.89:level=disabled[a]")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(graph),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{dur:.3f}", "-movflags", "+faststart", str(out)], check=True)
    return out


def render_video(work, props, out):
    raw = work / "raw.mp4"
    _remotion(["render", "src/index.ts", "NewsShort", str(raw), "--muted", f"--concurrency={speech.workers()}"], work)
    out.parent.mkdir(parents=True, exist_ok=True)
    mix_audio(work, props, raw, out)
    raw.unlink()
    return out


def render_stills(work, frames, out_dir):
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
    ap.add_argument("--variant", default="editorial", choices=VARIANTS)
    ap.add_argument("--voice", default="edge", choices=["edge", "gemini", "silent"])
    ap.add_argument("--tone", help=f"gemini preset: {', '.join(voices.PRESETS)}")
    ap.add_argument("--edge-voice", default="eka", choices=list(speech.EDGE_VOICES))
    ap.add_argument("--still", help="comma-separated frame numbers: PNG stills instead of the video")
    ap.add_argument("--out", default=str(ROOT / "out"))
    a = ap.parse_args()
    work, props = build(a.story, a.variant, a.voice, a.tone, speech.EDGE_VOICES[a.edge_voice])
    if a.still:
        for p in render_stills(work, [int(x) for x in a.still.split(",")], pathlib.Path(a.out) / "stills"):
            print(p)
    else:
        out = render_video(work, props, pathlib.Path(a.out) / f"{props['id']}-{a.variant}{'' if a.voice == 'gemini' else '-' + a.voice}.mp4")
        print(f"{out} | {props['durationInFrames'] / FPS:.1f}s | {len(props['scenes'])} scenes | music {props['music']}")
