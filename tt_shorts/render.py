"""Render one story JSON into a 1080x1920 tbilisi.today Short (forked from sitech-shorts shorts/render.py).

  voice   Gemini TTS (GEMINI_API_KEY) with a tone preset from voices.py; word timings by forced alignment (align.py).
          --silent renders a design preview without a voice: words get estimated timings, the music plays alone.
  frames  each scene is an HTML page (templates.py); Playwright pauses its CSS animations and screenshots every frame
  video   one ffmpeg pass: frames + word-highlight captions + loudnorm voice + the family's music, ducked under the voice

Text that would overflow is shrunk to fit before capture; anything still overflowing fails QA.
Usage: python -m tt_shorts.render stories/<id>.json [--theme A|B|C] [--silent] [--voice anchor] [--out out/]
"""
import argparse
import asyncio
import base64
import glob
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
import zlib

from fontTools.ttLib import TTFont
from playwright.async_api import Error as PlaywrightError, async_playwright

from tt_shorts import costs, normalize_ka, voices
from tt_shorts.templates import CAPTION_BOTTOM, H, HERO_BOTTOM, RAIL_X, W, cta_for, family, palette, scene_page

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FPS = 30
GEMINI_TTS = os.environ.get("SHORTS_GEMINI_TTS", "gemini-3.8-flash-tts")
ALIGN_PYTHON = os.environ.get("ALIGN_PYTHON", sys.executable)
PAGES = 3
CHUNK = 45  # frames per capture job (1.5 s)
MIN_SCENE = {"where": 2.8, "sources": 2.8, "end": 3.5}  # seconds on screen
MIN_SCENE_DEFAULT = 2.5
LEND = 0.6  # seconds a short scene may borrow from a neighbour before it counts as too short
CAPTION_SIZE = 56  # px, libass units: the font's win ascent + descent
END_HOLD = 1.6  # the end card stays up after the last word: time to see the QR
MUSIC_DIR = ASSETS / "music"
MUSIC_DB = -8
MUSIC_FADE_IN, MUSIC_FADE_OUT = 1.2, 2.5


def music_for(story_id, category):
    """The story's loop, by category family; one of the family's two picked by the story id."""
    if os.environ.get("SHORTS_MUSIC", "on").lower() in ("off", "0", "no"):
        return None
    loops = sorted(MUSIC_DIR.glob(f"{family(category)}-*.m4a")) or sorted(MUSIC_DIR.glob("society-*.m4a"))
    return loops[zlib.crc32(str(story_id).encode()) % len(loops)] if loops else None


def audio_graph(duration, music, silent=False):
    """ffmpeg filter for the voice (input 1) and, when there is one, the looping music (input 2) -> [a]."""
    voice = "[1:a]" + ("anull" if silent else "loudnorm=I=-14:TP=-1.5:LRA=11") + ",apad"
    if not music:
        return voice + "[a]"
    db = float(os.environ.get("SHORTS_MUSIC_DB", MUSIC_DB)) + (4 if silent else 0)  # no voice: the bed is the sound
    out = max(0.0, duration - MUSIC_FADE_OUT)
    return (f"{voice},aresample=48000,aformat=channel_layouts=stereo,asplit[voice][key];"
            f"[2:a]aresample=48000,volume={db}dB,afade=t=in:d={MUSIC_FADE_IN},afade=t=out:st={out:.2f}:d={MUSIC_FADE_OUT}[bed];"
            f"[bed][key]sidechaincompress=threshold=0.03:ratio=4:attack=40:release=500[ducked];"
            f"[voice][ducked]amix=inputs=2:duration=first:normalize=0,atrim=0:{duration:.3f},alimiter=limit=0.8:level=disabled[a]")


FIT_JS = """(low) => {  // low: HERO_BOTTOM, where the captions' safe band begins
  document.getAnimations().forEach(a => { a.pause(); a.currentTime = 1e6; });  // measure the final state
  const bad = [];
  for (const el of document.querySelectorAll('[data-fit]')) {
    let fs = parseFloat(getComputedStyle(el).fontSize);
    while (el.scrollWidth > el.clientWidth + 2 && fs > 24) { fs -= 3; el.style.fontSize = fs + 'px'; }
    if (el.scrollWidth > el.clientWidth + 2) bad.push(el.textContent.slice(0, 40));
  }
  for (const el of document.querySelectorAll('[data-fit-h]')) {
    const max = +el.dataset.fitH;
    let fs = parseFloat(getComputedStyle(el).fontSize);
    while (el.scrollHeight > max && fs > 24) { fs -= 3; el.style.fontSize = fs + 'px'; }
    if (el.scrollHeight > max) bad.push(el.textContent.slice(0, 40));
  }
  for (const el of document.querySelectorAll('#hero > .a'))  // fitted text, cards, chips: none reaches the captions
    if (el.getBoundingClientRect().bottom > low) bad.push('low: ' + (el.textContent.trim().slice(0, 40) || el.tagName));
  return bad;
}"""
SEEK_JS = "ms => document.getAnimations().forEach(a => { a.pause(); a.currentTime = ms; })"


def norm(s):
    return re.sub(r"[\W_]", "", s.lower())  # any script: Georgian anchors must match too


def anchor(words, phrase, after=0):
    """(start time, next word index) of the scene's first words, searching after the previous scene.
    A number token in the anchor matches a gap of up to 4 spoken words (the voice reads numbers as words)."""
    want = [norm(p) for p in normalize_ka.tokens(phrase) if norm(p)]
    keys = [norm(w["text"]) for w in words]

    def end_of_match(i):
        j, gap = i, False
        for t in want:
            if any(c.isdigit() for c in t) and t not in keys[j:j + 1]:
                gap = True
                continue
            window = keys[j:j + 5] if gap else keys[j:j + 1]
            if t not in window:
                return None
            j += window.index(t) + 1
            gap = False
        return j + (4 if gap else 0)

    for i in range(after, len(keys) - len(want) + 1):
        if want and keys[i:i + len(want)] == want:
            return words[i]["start"], i + len(want)
    for i in range(after, len(keys)):
        end = end_of_match(i) if want and (keys[i] == want[0] or any(c.isdigit() for c in want[0])) else None
        if end is not None:
            return words[i]["start"], min(end, len(keys))
    raise ValueError(f"scene anchor not in narration: {phrase!r}")


def estimate_words(narration, start=0.3):
    """Preview timings without a voice: a word lasts by its letters, punctuation adds a pause. Close to the
    Gemini Georgian pace (~2.3 words/s), so a preview's scene lengths look like the real video's."""
    out, t = [], start
    for w in narration.split():
        letters = len(re.sub(r"\W", "", w))
        d = 0.14 + 0.068 * letters
        out.append({"text": w, "start": round(t, 3), "end": round(t + d, 3)})
        t += d + 0.05 + (0.42 if w[-1] in ".?!:“" else 0.18 if w[-1] in ",;" else 0)
    return out


def gemini_speak(text, wav, words_json, preset, slug=None):
    """Gemini TTS with the preset's voice and delivery (the style goes in speech_metadata, never in the text)."""
    body = {"model": GEMINI_TTS,
            "input": [{"type": "user_input", "content": [
                {"type": "text", "text": text, "annotations": [{"type": "speech_metadata", "style": preset["style"]}]}]}],
            "response_format": {"type": "audio", "mime_type": "audio/wav"},
            "generation_config": {"speech_config": [{"voice": preset["voice"]}]}}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/interactions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise ConnectionError(f"gemini tts HTTP {e.code}: {e.read()[:300]!r}")
    audio = next(c for st in out["steps"] for c in st.get("content", []) if c.get("type") == "audio")
    wav.write_bytes(base64.b64decode(audio["data"]))
    try:
        with wave.open(str(wav)) as w:
            seconds = w.getnframes() / w.getframerate()
    except (wave.Error, EOFError):
        seconds = 0
    costs.record_tts(GEMINI_TTS, out.get("usage"), seconds, text, slug)
    if words_json is None:  # a voice sample: no alignment needed
        return
    said = wav.with_suffix(".spoken.txt")
    said.write_text(text, encoding="utf-8")
    subprocess.run([ALIGN_PYTHON, "-m", "tt_shorts.align", str(wav), str(said), str(words_json), "ka"], cwd=ROOT,
                   check=True, env={**os.environ, "HF_HOME": os.environ.get("HF_HOME", str(ROOT / "data" / "hf"))})


def silent_track(path, seconds):
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=48000:cl=mono", "-t", f"{seconds:.2f}", str(path)], check=True)


def lend_time(starts, types, most=LEND):
    """A scene a little short of its minimum borrows up to `most` seconds from a neighbour with time to spare."""
    starts = list(starts)
    need = [MIN_SCENE.get(t, MIN_SCENE_DEFAULT) for t in types]
    for i in range(len(types)):
        short = need[i] - (starts[i + 1] - starts[i])
        if not 0 < short <= most:
            continue
        if i > 0:
            spare = (starts[i] - starts[i - 1]) - need[i - 1]
            take = min(short, max(0.0, spare))
            starts[i] -= take
            short -= take
        if short > 0 and i + 2 < len(starts):
            spare = (starts[i + 2] - starts[i + 1]) - need[i + 1]
            starts[i + 1] += min(short, max(0.0, spare))
    return starts


def voice_qa(spoken, heard, min_ratio=0.5):
    """Words of the spoken text that the aligner's transcript barely contains: the voice may have skipped them."""
    import difflib
    geo = re.compile(r"[ა-ჰ]")
    words = spoken.split()
    chars, owner = [], []
    for i, w in enumerate(words):
        for c in w:
            if geo.match(c):
                chars.append(c)
                owner.append(i)
    sm = difflib.SequenceMatcher(None, chars, [c for c in heard if geo.match(c)], autojunk=False)
    hit = [False] * len(chars)
    for a, _, n in sm.get_matching_blocks():
        hit[a:a + n] = [True] * n
    per = {}
    for k, i in enumerate(owner):
        per.setdefault(i, []).append(hit[k])
    return [{"word": words[i].strip(".,;:!?„“\"()"), "score": round(sum(h) / len(h), 2)}
            for i, h in per.items() if len(h) >= 4 and sum(h) / len(h) < min_ratio]


def regroup(words, narration, say=None):
    pairs = normalize_ka.pairs(narration, say)
    counts = [len(spoken.split()) for _, spoken in pairs]
    if sum(counts) != len(words):
        raise RuntimeError(f"alignment has {len(words)} words, the spoken text {sum(counts)}")
    out, k = [], 0
    for (shown, _), n in zip(pairs, counts):
        part = words[k:k + n]
        out.append({"text": shown, "start": part[0]["start"], "end": part[-1]["end"]})
        k += n
    return out


def text_width(font, text, size=CAPTION_SIZE):
    """Width in px as libass draws it: libass sizes a font by its OS/2 win ascent + descent."""
    os2, cmap, hmtx = font["OS/2"], font.getBestCmap(), font["hmtx"]
    return sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in text) * size / (os2.usWinAscent + os2.usWinDescent)


def ass_color(hex_, alpha="00"):
    return f"&H{alpha}{hex_[5:7]}{hex_[3:5]}{hex_[1:3]}&"  # #RRGGBB -> ASS &HAABBGGRR&


def captions(words, path, font, p):
    """Up to 3 words per caption, never across a pause, never wider than the safe band; the word being spoken is
    in the accent. Theme colors: cap_fg text on a cap_box box. The box ends at CAPTION_BOTTOM, left of the rail."""
    fg, hi = ass_color(p["cap_fg"]), ass_color(p["cap_hi"])

    def ts(s):
        return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"

    side = W - RAIL_X
    room = W - 2 * side - 2 * 20
    head = ("[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Cap,{font['name'].getDebugName(1)},{CAPTION_SIZE},{fg},{fg},{ass_color(p['cap_box'], '10')},&H00000000,0,0,0,0,100,100,0,0,3,20,0,2,"
            f"{side},{side},{H - CAPTION_BOTTOM + 20},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    chunks = [[words[0]]]
    for prev, w in zip(words, words[1:]):
        wide = text_width(font, " ".join(x["text"] for x in chunks[-1] + [w])) > room
        if len(chunks[-1]) == 3 or w["start"] - prev["end"] > 0.2 or wide:
            chunks.append([])
        chunks[-1].append(w)
    lines = []
    for n, chunk in enumerate(chunks):
        nxt = chunks[n + 1][0]["start"] if n + 1 < len(chunks) else chunk[-1]["end"] + 0.4
        nxt = min(nxt, chunk[-1]["end"] + 0.35)
        for j, w in enumerate(chunk):
            end = chunk[j + 1]["start"] if j + 1 < len(chunk) else nxt
            body = " ".join("{\\c" + hi + "}" + x["text"] + "{\\c" + fg + "}" if k == j else x["text"]
                            for k, x in enumerate(chunk))
            lines.append(f"Dialogue: 0,{ts(w['start'])},{ts(end)},Cap,,0,0,0,,{body}")
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def caption_font(work):
    """One static bold TTF for libass: Noto Sans Georgian (it has Latin and digits too)."""
    from fontTools.varLib import instancer
    fonts = work / "fonts"
    shutil.rmtree(fonts, ignore_errors=True)
    fonts.mkdir()
    ttf = fonts / "caption-ka.ttf"
    instancer.instantiateVariableFont(TTFont(ASSETS / "fonts" / "NotoSansGeorgian.ttf"), {"wght": 700, "wdth": 100}).save(ttf)
    return fonts, TTFont(ttf)


def browser_path():
    if os.environ.get("SHORTS_CHROMIUM"):
        return os.environ["SHORTS_CHROMIUM"]
    found = sorted(glob.glob("/root/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell") +
                   glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell"))
    return found[-1] if found else None


def workers():
    try:
        return max(1, int(os.environ["SHORTS_RENDER_WORKERS"]))
    except (KeyError, ValueError):
        return max(PAGES, min(8, (os.cpu_count() or 4) - 2))


async def capture(jobs, frames_dir):
    """jobs: (html_path, first_frame_index, frame_count). Returns QA problems. Each frame is a seek into paused
    CSS animations, so scenes split into CHUNK-frame pieces that any page can take."""
    problems = set()
    queue = asyncio.Queue()
    for src, first, count in jobs:
        for off in range(0, count, CHUNK):
            queue.put_nowait((src, first, off, min(CHUNK, count - off)))
    n = workers()
    async with async_playwright() as p:
        browsers = [await p.chromium.launch(executable_path=browser_path(),
                                            args=["--no-sandbox", "--allow-file-access-from-files", "--hide-scrollbars"])
                    for _ in range(max(1, min(3, n // 3)))]

        async def worker(browser):
            page = await browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            while not queue.empty():
                src, first, off, count = queue.get_nowait()
                for tries in range(3):
                    try:
                        await page.goto(f"file://{src}", wait_until="load")
                        await page.evaluate("document.fonts.ready.then(() => 1)")
                        bad = await page.evaluate(FIT_JS, HERO_BOTTOM)
                        for f in range(off, off + count):
                            await page.evaluate(SEEK_JS, 100 + f * 1000 / FPS)
                            await page.screenshot(path=str(frames_dir / f"{first + f:05d}.jpg"), type="jpeg", quality=94)
                        problems.update(f"{src.stem}: {b}" for b in bad)
                        break
                    except PlaywrightError:
                        if tries == 2:
                            raise
                        await page.close()
                        page = await browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            await page.close()

        await asyncio.gather(*(worker(browsers[i % len(browsers)]) for i in range(n)))
        for b in browsers:
            await b.close()
    return sorted(problems)


def voice_track(story, work, silent, preset_name):
    """-> (audio file, display words with timings). Gemini when not silent; cached by voice + spoken text."""
    narration, say = story["narration"], story.get("say")
    if silent:
        words = estimate_words(narration)
        audio = work / "silence.wav"
        silent_track(audio, words[-1]["end"] + 0.5)
        return audio, words
    preset = voices.preset(preset_name or story.get("voice"), story.get("category"))
    spoken = normalize_ka.speech(narration, say)
    audio, words_json, said = work / "voice.wav", work / "words.json", work / "voice.txt"
    key = f"gemini|{preset['voice']}|{preset['style']}|{spoken}"
    if not words_json.exists() or not said.exists() or said.read_text(encoding="utf-8") != key:
        words_json.unlink(missing_ok=True)
        gemini_speak(spoken, audio, words_json, preset, slug=str(story["id"]))
        said.write_text(key, encoding="utf-8")
    words = regroup(json.loads(words_json.read_text(encoding="utf-8")), narration, say)
    heard = words_json.with_name("words.heard.txt")
    if heard.exists():
        story.setdefault("qa", {})["voice"] = voice_qa(spoken, heard.read_text(encoding="utf-8"))
    return audio, words


def render(story_path, out_dir, theme="A", silent=False, voice=None, platform="shorts"):
    story = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    sid = story["id"]
    name = f"{sid}-{theme}" + ("-preview" if silent else "")
    work = ROOT / "work" / name
    work.mkdir(parents=True, exist_ok=True)
    timings = {}

    t0 = time.time()
    audio, words = voice_track(story, work, silent, voice)
    timings["voice"] = time.time() - t0

    category = story.get("category", "society")
    ctx = {"assets": ASSETS, "id": sid, "date": story["date"], "sources": story.get("sources", []),
           "category": category, "theme": theme, "cta": story.get("cta") or cta_for(sid), "platform": platform}
    scenes = story["scenes"]
    audio_end = words[-1]["end"] + END_HOLD
    starts, after = [0.0], 0
    for s in scenes[1:]:
        t, after = anchor(words, s["at"], after)
        starts.append(t - 0.08)
    starts.append(audio_end)
    starts = lend_time(starts, [s["type"] for s in scenes])
    marks = [round(t * FPS) for t in starts]
    if any(b <= a for a, b in zip(marks, marks[1:])):
        raise ValueError("scene anchors are out of order")
    short = [f"scene {i} ({s['type']}) is on screen {(b - a) / FPS:.1f}s, needs {MIN_SCENE.get(s['type'], MIN_SCENE_DEFAULT)}s"
             for i, (s, a, b) in enumerate(zip(scenes, marks, marks[1:]))
             if (b - a) / FPS < MIN_SCENE.get(s["type"], MIN_SCENE_DEFAULT)]
    if short:
        raise RuntimeError("layout QA failed: " + "; ".join(short))

    t0 = time.time()
    frames = work / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()
    jobs = []
    for i, s in enumerate(scenes):
        count = marks[i + 1] - marks[i]
        src = work / f"scene{i}.html"
        src.write_text(scene_page(s, ctx, count / FPS), encoding="utf-8")
        jobs.append((src, marks[i], count))
    jobs.sort(key=lambda j: -j[2])
    problems = asyncio.run(capture(jobs, frames))
    timings["frames"] = time.time() - t0
    if problems:
        raise RuntimeError("layout QA failed: " + "; ".join(problems))

    t0 = time.time()
    fonts, font = caption_font(work)
    ass = work / "captions.ass"
    captions(words, ass, font, palette(theme, category))
    out = pathlib.Path(out_dir) / f"{name}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    music = music_for(sid, category)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-framerate", str(FPS), "-i", str(frames / "%05d.jpg"), "-i", str(audio),
                    *(["-stream_loop", "-1", "-i", str(music)] if music else []),
                    "-filter_complex", f"[0:v]ass={ass}:fontsdir={fonts},format=yuv420p[v];" +
                    audio_graph(marks[-1] / FPS, music, silent),
                    "-map", "[v]", "-map", "[a]", "-frames:v", str(marks[-1]),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-threads", "0", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(out)], check=True)
    timings["encode"] = time.time() - t0
    shutil.rmtree(frames, ignore_errors=True)
    print(" | ".join(f"{k} {v:.1f}s" for k, v in timings.items()) +
          f" | video {marks[-1] / FPS:.1f}s | music {music.stem if music else '-'} | {out.stat().st_size / 1e6:.1f} MB -> {out}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--theme", default="A", choices=["A", "B", "C"])
    ap.add_argument("--silent", action="store_true", help="design preview: estimated timings, music only")
    ap.add_argument("--voice", help=f"tone preset: {', '.join(voices.PRESETS)}")
    ap.add_argument("--out", default=str(ROOT / "out"))
    a = ap.parse_args()
    render(a.story, a.out, a.theme, a.silent, a.voice)
