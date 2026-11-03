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

from tt_shorts import brand, catalog, costs, normalize_ka, voices

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FPS = 30
GEMINI_TTS = os.environ.get("SHORTS_GEMINI_TTS", "gemini-3.8-flash-tts")
ALIGN_PYTHON = os.environ.get("ALIGN_PYTHON", sys.executable)
EDGE_VOICES = {"eka": "ka-GE-EkaNeural", "giorgi": "ka-GE-GiorgiNeural"}
# seconds on screen at least, per scene type (brushes/<type>.json min_seconds): a chart or a drawing builds up and
# must then be seen
MIN_SCENE = catalog.min_scene()
MIN_SCENE_DEFAULT = catalog.MIN_SECONDS_DEFAULT
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


GEORGIAN_NUMERALS = {
    # Units
    "ნული": 0, "ერთი": 1, "ორი": 2, "სამი": 3, "ოთხი": 4, "ხუთი": 5, "ექვსი": 6, "შვიდი": 7, "რვა": 8, "ცხრა": 9,
    "ერთ": 1, "ორ": 2, "სამ": 3, "ოთხ": 4, "ხუთ": 5, "ექვს": 6, "შვიდ": 7,
    # Teens (10-19)
    "ათი": 10, "ათ": 10, "თერთმეტი": 11, "თორმეტი": 12, "ცამეტი": 13, "თოთხმეტი": 14, "თხუთმეტი": 15,
    "თექვსმეტი": 16, "ჩვიდმეტი": 17, "თვრამეტი": 18, "ცხრამეტი": 19,
    # Vigesimal base-20 compounds (20-99)
    "ოცი": 20, "ოც": 20, "ორმოცი": 40, "ორმოც": 40, "სამოცი": 60, "სამოც": 60, "ოთხმოცი": 80, "ოთხმოც": 80,
    # Hundreds
    "ასი": 100, "ას": 100, "ორასი": 200, "ორას": 200, "სამასი": 300, "სამას": 300,
    "ოთხასი": 400, "ოთხას": 400, "ხუთასი": 500, "ხუთას": 500, "ექვსასი": 600, "ექვსას": 600,
    "შვიდასი": 700, "შვიდას": 700, "რვაასი": 800, "რვაას": 800, "ცხრაასი": 900, "ცხრაას": 900,
}

TWENTY_PREFIXES = {
    "ოცდა": 20, "ორმოცდა": 40, "სამოცდა": 60, "ოთხმოცდა": 80,
}

MULTIPLIERS = {
    "ათასი": 1000, "ათას": 1000,
    "მილიონი": 1000000, "მილიონ": 1000000,
    "მილიარდი": 1000000000, "მილიარდ": 1000000000,
}


def parse_georgian_numeral_word(w):
    w = w.strip(".,;:!?„“\"()[]{}")
    if not w:
        return None
    if w in GEORGIAN_NUMERALS:
        return GEORGIAN_NUMERALS[w]
    for pre, base in TWENTY_PREFIXES.items():
        if w.startswith(pre):
            rest = w[len(pre):]
            if rest in GEORGIAN_NUMERALS:
                return base + GEORGIAN_NUMERALS[rest]
    return None


def extract_numbers(text):
    """Extract all numbers from text (both digits and Georgian number words).
    Returns list of numeric values (ints or floats).
    """
    out = []
    digit_rx = re.compile(r"(?<![\w])(\d+(?:[.,]\d+)?)(?![\w])")
    for m in digit_rx.finditer(text):
        val_str = m.group(1).replace(",", ".")
        try:
            val = float(val_str) if "." in val_str else int(val_str)
            out.append(val)
        except ValueError:
            pass

    words = re.findall(r"[ა-ჰ]+", text)
    i = 0
    while i < len(words):
        w = words[i]
        val = parse_georgian_numeral_word(w)
        mult = MULTIPLIERS.get(w)
        if val is not None:
            current = val
            j = i + 1
            while j < len(words):
                next_w = words[j]
                next_val = parse_georgian_numeral_word(next_w)
                next_mult = MULTIPLIERS.get(next_w)
                if next_mult is not None:
                    current = (current if current > 0 else 1) * next_mult
                    j += 1
                elif next_val is not None:
                    current += next_val
                    j += 1
                else:
                    break
            out.append(current)
            i = j
        elif mult is not None:
            out.append(mult)
            i += 1
        else:
            i += 1

    return out


def numeral_problems(spoken, heard):
    """Check that numbers in spoken text are heard with the exact same values.
    Returns findings with score 0.0 when a number is missed or heard as another number.
    """
    sp_nums = extract_numbers(spoken)
    hd_nums = extract_numbers(heard)
    if not sp_nums:
        return []

    mismatches = []
    remaining_hd = list(hd_nums)
    for expected in sp_nums:
        if expected in remaining_hd:
            remaining_hd.remove(expected)
        else:
            mismatches.append({
                "word": f"number {expected}",
                "score": 0.0,
                "number_mismatch": True,
                "expected": expected,
                "heard": hd_nums,
            })
    return mismatches


def voice_qa(spoken, heard, min_ratio=0.5):
    """Words of the spoken text that the aligner's transcript barely contains: the voice may have skipped them,
    or read numbers as different values (Lemo-Opuscar numeral check)."""
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
    findings = [{"word": words[i].strip(".,;:!?„“\"()"), "score": round(sum(h) / len(h), 2)}
                for i, h in per.items() if len(h) >= 4 and sum(h) / len(h) < min_ratio]
    findings += numeral_problems(spoken, heard)
    return findings


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


def scene_frames(story, words, hold=END_HOLD):
    """Start frame of every scene plus the last frame; `hold` is the time after the last word (swipe.HOLD per outro)."""
    scenes = story["scenes"]
    starts, after = [0.0], 0
    for s in scenes[1:]:
        t, after = anchor(words, s["at"], after)
        starts.append(max(starts[-1] + 0.1, t - 0.08))
    starts.append(words[-1]["end"] + hold)
    starts = lend_time(starts, [s["type"] for s in scenes])
    marks = [round(t * FPS) for t in starts]
    short = [f"scene {i} ({s['type']}) is on screen {(b - a) / FPS:.1f}s"
             for i, (s, a, b) in enumerate(zip(scenes, marks, marks[1:]))
             if (b - a) / FPS < MIN_SCENE.get(s["type"], MIN_SCENE_DEFAULT)]
    if short:
        raise RuntimeError("layout QA failed: " + "; ".join(short))
    return marks


def mark_frames(scenes, words, frames, story_id, family):
    """Each scene's voice-synced mark (its "em", marks.py): the frame its phrase starts being said, from the word
    timings, and how it is drawn; None for a scene without one. frames: scene_frames' start frames (+ the last)."""
    from tt_shorts import marks
    return [marks.resolve(s, i, story_id, family, words, a, b - a, FPS) if s.get("em") else None
            for i, (s, a, b) in enumerate(zip(scenes, frames, frames[1:]))]
