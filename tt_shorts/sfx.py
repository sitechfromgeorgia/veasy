"""Sound effects on the timeline: which accent sounds when, and one track of them for the mix (format key `sfx`).

The cues come from the video's own timeline (the props every engine gets), never from the writer:

    a cut between scenes          whoosh (click for a plain "cut" transition), centred on the cut's motion
    a mark landing (em)           pop, when the stroke starts (speech.mark_frames: when the voice says it)
    the outro chip coming in      pop
    a stat's number counting      tick every TICK_EVERY frames while it counts (click for the flap board), then
                                  a soft thud as it settles
    a chart's bars or cells       blip as each one starts to grow (bars, compare, share)
    a scenario beat               sound cue matched to the beat's job (Promise -> whoosh/pop,
                                  Setup -> click/whoosh, False lead -> blip/click,
                                  Complication -> tick/blip, Turn -> pop/whoosh,
                                  Payoff -> thud/pop, Resolution -> click/pop)

The sounds are tools/compose_sfx.py's (synthesized, ours, deterministic). track() lays them on one stereo WAV at
their own level; props.mix_audio puts that track under the voice at one constant level (LEVEL_DB): no ducking, no
risers, nothing that rises and falls under the speech (the owner's music rule). Remotion never sees a cue: the mix
is ffmpeg's, so a HyperFrames film gets the same sound from the same props.

    cues(props) -> [{"t": seconds, "name": "whoosh"}, ...]   sorted, at least MIN_GAP apart
"""
import contextlib
import pathlib
import runpy
import sys
import wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "assets" / "sfx"
NAMES = ("click", "pop", "whoosh", "tick", "thud", "blip")
SR = 48000
FPS = 30
LEVEL_DB = -6.0  # the whole track, under the -16 LUFS voice: accents a little above the music bed, never louder
MIN_GAP = 0.06  # seconds: two accents closer than this are one
TICK_EVERY = 3  # frames between two ticks of a counting number
COUNT_DELAY, COUNT_FRAMES = 4, 32  # remotion/src/scenes/index.tsx Stat: the number counts from frame 4 for 32
WHOOSH_LEAD = 0.1  # a whoosh starts this much before the cut, so its middle lands on the moving scene
CHART_STEP = 10  # frames between two bars' starts (remotion/src/scenes: 6 + i * 10)
# Cues tailored per transition: snaps on cuts/louvers, pop on iris, whoosh on sweeps, silent on fade
CUT_SOUND = {
    "cut": "click",
    "shutter": "click",
    "blind": "click",
    "iris": "pop",
    "meter": "blip",
    "line": "whoosh",
    "panel": "whoosh",
    "wipe": "whoosh",
    "slide": "whoosh",
    "push": "whoosh",
    "split": "whoosh",
    "corner": "whoosh",
    "fade": None,
}
# Scenario beat jobs mapped to canonical sound cues:
#   promise (hook)               -> whoosh (alternate: pop)
#   setup (context)              -> click (alternate: whoosh)
#   false_lead                   -> blip (alternate: click)
#   complication (evidence)      -> tick (alternate: blip)
#   turn (peripeteia)            -> pop (alternate: whoosh)
#   payoff (climax / answer)     -> thud (alternate: pop)
#   resolution                   -> click (alternate: pop)
BEAT_JOB_SOUNDS = {
    "promise": "whoosh",
    "hook": "whoosh",
    "setup": "click",
    "context": "click",
    "false_lead": "blip",
    "false-lead": "blip",
    "false lead": "blip",
    "complication": "tick",
    "evidence": "tick",
    "turn": "pop",
    "peripeteia": "pop",
    "payoff": "thud",
    "climax": "thud",
    "answer": "thud",
    "resolution": "click",
    "resolve": "click",
    "outro": "click",
}

BEAT_JOB_ALTERNATES = {
    "promise": "pop",
    "hook": "pop",
    "setup": "whoosh",
    "context": "whoosh",
    "false_lead": "click",
    "false-lead": "click",
    "false lead": "click",
    "complication": "blip",
    "evidence": "blip",
    "turn": "whoosh",
    "peripeteia": "whoosh",
    "payoff": "pop",
    "climax": "pop",
    "answer": "pop",
    "resolution": "pop",
    "resolve": "pop",
    "outro": "pop",
}

# The pair of canonical sound cues per beat job: (primary, alternate)
BEAT_JOB_ALLOWED = {
    "promise": ("whoosh", "pop"),
    "hook": ("whoosh", "pop"),
    "setup": ("click", "whoosh"),
    "context": ("click", "whoosh"),
    "false_lead": ("blip", "click"),
    "false-lead": ("blip", "click"),
    "false lead": ("blip", "click"),
    "complication": ("tick", "blip"),
    "evidence": ("tick", "blip"),
    "turn": ("pop", "whoosh"),
    "peripeteia": ("pop", "whoosh"),
    "payoff": ("thud", "pop"),
    "climax": ("thud", "pop"),
    "answer": ("thud", "pop"),
    "resolution": ("click", "pop"),
    "resolve": ("click", "pop"),
    "outro": ("click", "pop"),
}

OPTIONS = {"off": "no sound effects (the default: renders are as before)",
           "on": "short accents on the timeline: a whoosh on a cut, a pop when a mark lands, ticks while a number "
                 "counts, blips as bars grow; one constant level under the voice, no ducking"}


def normalize_job(job):
    """Normalize a beat job identifier to a canonical key (e.g. 'False Lead' -> 'false_lead')."""
    if not job:
        return "setup"
    return str(job).strip().lower().replace("-", "_").replace(" ", "_")


def allowed_sounds_for_beat(job):
    """The allowed sound cues for a beat job -> (primary, alternate). Defaults to ('pop', 'click')."""
    k = normalize_job(job)
    return BEAT_JOB_ALLOWED.get(k, ("pop", "click"))


def sound_for_beat(job, sound=None, alternate=False):
    """The sound cue name for a scenario beat job: explicit sound if given in NAMES, else primary/alternate."""
    if sound and sound in NAMES:
        return sound
    k = normalize_job(job)
    table = BEAT_JOB_ALTERNATES if alternate else BEAT_JOB_SOUNDS
    return table.get(k, "pop")


def _load_scenario(scenario_id):
    """Load a scenario dict by id from tt_shorts.scenarios or scenarios/<id>.json if available."""
    try:
        from tt_shorts import scenarios
        if hasattr(scenarios, "get"):
            sc = scenarios.get(scenario_id)
            if sc and isinstance(sc, dict):
                return sc
    except Exception:
        pass
    p = ROOT / "scenarios" / f"{scenario_id}.json"
    if p.is_file():
        try:
            import json
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def scenario_beats(props):
    """The active scenario beats of one video from props (list of beat dicts, or [])."""
    if not props:
        return []
    if "scenario_beats" in props and isinstance(props["scenario_beats"], list):
        return props["scenario_beats"]
    sc = props.get("scenario")
    if isinstance(sc, dict) and "beats" in sc and isinstance(sc["beats"], list):
        return sc["beats"]
    if isinstance(sc, list) and sc:  # chapters: one plot each (scenarios.chapter_beats)
        try:
            from tt_shorts import scenarios
            return [b for _, _, beats in scenarios.chapter_beats(sc) for b in beats]
        except Exception:
            return []
    if isinstance(sc, str) and sc:
        loaded = _load_scenario(sc)
        if loaded and "beats" in loaded and isinstance(loaded["beats"], list):
            return loaded["beats"]
    # Check if individual scenes have beat metadata
    scenes = props.get("scenes") or []
    has_beats = any(s.get("beat") or s.get("job") or s.get("sfx") for s in scenes)
    if has_beats:
        out = []
        for s in scenes:
            b = s.get("beat")
            if isinstance(b, dict):
                out.append(b)
            elif isinstance(b, str):
                out.append({"job": b, "sound_cue": s.get("sfx")})
            elif s.get("job"):
                out.append({"job": s["job"], "sound_cue": s.get("sfx")})
            elif s.get("sfx"):
                out.append({"job": "setup", "sound_cue": s["sfx"]})
            else:
                out.append({})
        return out
    return []


def beat_for_scene(idx, scene, beats):
    """The beat dict for scene `idx`, or None."""
    s_beat = scene.get("beat")
    if isinstance(s_beat, dict):
        return s_beat
    if isinstance(s_beat, str):
        return {"job": s_beat, "sound_cue": scene.get("sfx")}
    if scene.get("job"):
        return {"job": scene["job"], "sound_cue": scene.get("sfx")}
    if scene.get("sfx"):
        return {"job": "setup", "sound_cue": scene["sfx"]}
    if beats and 0 <= idx < len(beats):
        b = beats[idx]
        if isinstance(b, dict):
            return b
        if isinstance(b, str):
            return {"job": b}
    return None


def files_ready():
    return all((DIR / f"{n}.wav").is_file() for n in NAMES)


def ensure():
    """The sound files, composed once when they are missing (tools/compose_sfx.py, under a second)."""
    if not files_ready():  # its report goes to stderr: an engine command's stdout is its JSON
        with contextlib.redirect_stdout(sys.stderr):
            runpy.run_path(str(ROOT / "tools" / "compose_sfx.py"), run_name="veasy_sfx")["main"](DIR)
    return DIR


def cues(props):
    """The accents of one video, from its props' timeline -> [{t, name}] (seconds)."""
    out = []
    scenes = props.get("scenes") or []
    beats = scenario_beats(props)
    for i, s in enumerate(scenes):
        a = s["from"]
        b = beat_for_scene(i, s, beats)
        b_job = normalize_job(b.get("job")) if b else None
        if b and "sound" in b and b["sound"] is None:  # a scenario beat that declares no cue has none
            b_snd = None
        else:
            b_snd = sound_for_beat(b_job, b.get("sound_cue") or b.get("sfx") or b.get("sound")) if b else None
        b_sync = b.get("sync", "auto") if b else "auto"

        # 1. Entrance / cut cue
        if i == 0:
            # Promise / hook entrance: opens the video with its sound cue
            if b_snd and b_sync in ("auto", "cut", "start", "both"):
                lead = WHOOSH_LEAD if b_snd == "whoosh" else 0.0
                out.append({"t": max(0.0, a / FPS - lead), "name": b_snd})
        else:
            tr = s.get("transition") or props.get("transition") or "line"
            snd = CUT_SOUND.get(tr, "whoosh")
            if b_snd:
                if b_sync in ("cut", "both"):
                    snd = b_snd
                elif b_sync == "auto":
                    # For setup/resolution beats, or scenes without em marks, beat sound shapes the cut
                    if not s.get("mark") or b_job in ("setup", "context", "resolution", "resolve", "outro"):
                        snd = b_snd
            if snd:
                lead = WHOOSH_LEAD if snd == "whoosh" else 0.0
                out.append({"t": max(0.0, a / FPS - lead), "name": snd})

        # 2. Mark cue (em)
        m = s.get("mark")
        if m and isinstance(m.get("at"), (int, float)):
            mark_snd = "pop"
            if b_snd:
                if b_sync in ("mark", "both"):
                    mark_snd = b_snd
                elif b_sync == "auto":
                    # Dramatic revelation/twist/climax marks take the beat cue
                    if b_job in ("false_lead", "complication", "evidence", "turn", "peripeteia", "payoff", "climax", "answer"):
                        mark_snd = b_snd
            out.append({"t": (a + m["at"]) / FPS, "name": mark_snd})

        # 3. Visual counter / chart cues
        t = s.get("type")
        if t == "stat" and not s.get("isotype"):
            flap = s.get("style") == "flap"
            end = min(s.get("duration", 0), COUNT_DELAY + COUNT_FRAMES)
            for f in range(COUNT_DELAY, end, TICK_EVERY):
                out.append({"t": (a + f) / FPS, "name": "click" if flap else "tick"})
            if end > COUNT_DELAY:
                out.append({"t": (a + end) / FPS, "name": "thud"})
        if t in ("bars", "compare"):
            for k in range(len(s.get("items") or [])):
                f = 6 + k * CHART_STEP
                if f < s.get("duration", 0):
                    out.append({"t": (a + f) / FPS, "name": "blip"})
        if t == "share":
            out.append({"t": (a + 8) / FPS, "name": "blip"})

    if props.get("outroFrom"):
        out.append({"t": props["outroFrom"] / FPS, "name": "pop"})

    end = props.get("durationInFrames", 0) / FPS
    kept = []
    for c in sorted(out, key=lambda c: (c["t"], NAMES.index(c["name"]))):
        if end and c["t"] >= end - 0.05:
            continue
        if kept and c["t"] - kept[-1]["t"] < MIN_GAP:
            continue
        kept.append({"t": round(c["t"], 3), "name": c["name"]})
    return kept


def _read(name):
    with wave.open(str(DIR / f"{name}.wav"), "rb") as w:
        if w.getframerate() != SR or w.getnchannels() != 1:
            raise ValueError(f"assets/sfx/{name}.wav: 48 kHz mono expected (run tools/compose_sfx.py)")
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32767


def track(cue_list, seconds, out):
    """The cues on one stereo 48 kHz WAV of `seconds` (each sound at its file's level; the mix sets the track's)."""
    ensure()
    n = int(round(seconds * SR))
    mono = np.zeros(n, dtype=np.float32)
    sounds = {}
    for c in cue_list:
        x = sounds.setdefault(c["name"], _read(c["name"]))
        a = int(round(c["t"] * SR))
        if a >= n:
            continue
        b = min(n, a + len(x))
        mono[a:b] += x[:b - a]
    pcm = (np.clip(mono, -0.99, 0.99) * 32767).round().astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    out = pathlib.Path(out)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    return out
