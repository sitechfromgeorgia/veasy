"""Voice and timing for Veasy videos: the voice track, its word timings and the scene start times.

  gemini   production voice: Gemini TTS with a tone preset (voices.py); word timings by forced alignment (align.py)
  edge     preview stand-in until the Gemini key is on the machine: Microsoft's free ka-GE neural voices, which
           return word timings with the audio, so captions and cuts are real
  silent   no voice: timings estimated from the letters, the music plays alone

Scenes start at their `at` anchors (the first words of the scene in the narration). A scene shorter than its
minimum borrows a little from a neighbour (lend_time); if it is still too short the script goes back to the writer.
Forked from sitech-shorts shorts/render.py (the frame renderer is Remotion now: remotion/).
"""
import asyncio
import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request
import wave
import zlib

from tt_shorts import brand, costs, normalize_ka, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FPS = 30
GEMINI_TTS = os.environ.get("SHORTS_GEMINI_TTS", "gemini-3.8-flash-tts")
ALIGN_PYTHON = os.environ.get("ALIGN_PYTHON", sys.executable)
EDGE_VOICES = {"eka": "ka-GE-EkaNeural", "giorgi": "ka-GE-GiorgiNeural"}
MIN_SCENE = {"where": 2.8, "sources": 2.8, "end": 3.5}  # seconds on screen
MIN_SCENE_DEFAULT = 2.5
LEND = 0.6  # seconds a short scene may borrow from a neighbour before it counts as too short
END_HOLD = 1.6  # the end card stays up after the last word: time to see the QR
MUSIC_DIR = ASSETS / "music"


def music_for(story_id, fam):
    """The story's loop for a music family (meta.family gives a category's); one of the family's loops picked by
    the story id."""
    if os.environ.get("SHORTS_MUSIC", "on").lower() in ("off", "0", "no"):
        return None
    loops = sorted(MUSIC_DIR.glob(f"{fam}-*.m4a")) or sorted(MUSIC_DIR.glob("society-*.m4a"))
    return loops[zlib.crc32(str(story_id).encode()) % len(loops)] if loops else None


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


def split_like(w):
    """One timed token holding several words ("In 2025") -> one per word, sharing the time."""
    parts = w["text"].split()
    step = (w["end"] - w["start"]) / max(1, len(parts))
    return [{"text": t, "start": w["start"] + k * step, "end": w["start"] + (k + 1) * step} for k, t in enumerate(parts)]


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
                {"type": "text", "text": text,
                 # an empty style is a valid choice (Google: try none first); then send no annotation at all
                 **({"annotations": [{"type": "speech_metadata", "style": preset["style"]}]} if preset["style"] else {})}]}],
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


def workers():
    """Render concurrency: SHORTS_RENDER_WORKERS, else most of the CPUs (the server runs the agent too)."""
    try:
        return max(1, int(os.environ["SHORTS_RENDER_WORKERS"]))
    except (KeyError, ValueError):
        return max(2, min(8, (os.cpu_count() or 4) - 1))


async def _edge(text, voice, mp3):
    import ssl

    import edge_tts
    import edge_tts.communicate as ec
    if os.environ.get("SSL_CERT_FILE"):  # behind a TLS-inspecting proxy edge-tts' own certifi bundle fails
        ec._SSL_CTX = ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"])
    words = []
    with open(mp3, "wb") as f:
        async for ch in edge_tts.Communicate(text, voice, boundary="WordBoundary").stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7
                words.append({"text": ch["text"], "start": s, "end": s + ch["duration"] / 1e7})
    return words


def to_display(spoken_words, narration, say):
    """Spoken-word timings -> display-word timings ("6400" is said as three words). Exact when the counts agree,
    else each display word gets the span of its share of the spoken letters."""
    pairs = normalize_ka.pairs(narration, say)
    flat = [w for x in spoken_words for w in ([x] if len(x["text"].split()) == 1 else split_like(x))]
    try:
        return regroup(flat, narration, say)
    except RuntimeError:
        pass
    total = sum(len(sp) for _, sp in pairs) or 1
    t0, t1 = flat[0]["start"], flat[-1]["end"]
    out, acc = [], 0
    for shown, sp in pairs:
        a = t0 + (t1 - t0) * acc / total
        acc += len(sp)
        out.append({"text": shown, "start": round(a, 3), "end": round(t0 + (t1 - t0) * acc / total, 3)})
    return out


def voice_key(story, engine, tone, edge_voice):
    """What makes a voice track unique (engine, voice, style, the exact spoken text), or None for silent.
    store.voice_dir(key) caches one track per key, so trying another tone never overwrites the first."""
    if engine == "silent":
        return None
    spoken = normalize_ka.speech(story["narration"], story.get("say"))
    if engine == "edge":
        return f"edge|{edge_voice}|{spoken}"
    preset = voices.preset(tone or story.get("voice"), story.get("category"), brand.of(story))
    return f"gemini|{preset['voice']}|{preset['style']}|{spoken}"


def voice(story, work, engine, tone, edge_voice):
    """-> (audio file or None, display words)."""
    narration, say = story["narration"], story.get("say")
    if engine == "silent":
        return None, estimate_words(narration)
    spoken = normalize_ka.speech(narration, say)
    if engine == "edge":
        mp3 = work / "voice.mp3"
        cache = work / "voice.edge.json"
        key = f"{edge_voice}|{spoken}"
        if cache.exists() and mp3.exists() and json.loads(cache.read_text(encoding="utf-8"))["key"] == key:
            words = json.loads(cache.read_text(encoding="utf-8"))["words"]
        else:
            words = asyncio.run(_edge(spoken, edge_voice, mp3))
            cache.write_text(json.dumps({"key": key, "words": words}, ensure_ascii=False), encoding="utf-8")
        return mp3, to_display(words, narration, say)
    preset = voices.preset(tone or story.get("voice"), story.get("category"), brand.of(story))
    audio, words_json, said = work / "voice.wav", work / "words.json", work / "voice.txt"
    key = f"gemini|{preset['voice']}|{preset['style']}|{spoken}"
    if not words_json.exists() or not said.exists() or said.read_text(encoding="utf-8") != key:
        words_json.unlink(missing_ok=True)
        gemini_speak(spoken, audio, words_json, preset, slug=str(story["id"]))
        said.write_text(key, encoding="utf-8")
    words = regroup(json.loads(words_json.read_text(encoding="utf-8")), narration, say)
    heard = words_json.with_name("words.heard.txt")
    if heard.exists():  # words the voice may have skipped or changed, for the daily report
        story.setdefault("qa", {})["voice"] = voice_qa(spoken, heard.read_text(encoding="utf-8"))
    return audio, words


def scene_frames(story, words):
    scenes = story["scenes"]
    starts, after = [0.0], 0
    for s in scenes[1:]:
        t, after = anchor(words, s["at"], after)
        starts.append(max(starts[-1] + 0.1, t - 0.08))
    starts.append(words[-1]["end"] + END_HOLD)
    starts = lend_time(starts, [s["type"] for s in scenes])
    marks = [round(t * FPS) for t in starts]
    short = [f"scene {i} ({s['type']}) is on screen {(b - a) / FPS:.1f}s"
             for i, (s, a, b) in enumerate(zip(scenes, marks, marks[1:]))
             if (b - a) / FPS < MIN_SCENE.get(s["type"], MIN_SCENE_DEFAULT)]
    if short:
        raise RuntimeError("layout QA failed: " + "; ".join(short))
    return marks
