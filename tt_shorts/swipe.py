"""Built for the swipe and the loop (ROADMAP D7).

On Shorts, Reels and TikTok the first frame decides whether people swipe away, and Shorts count every replay as a
view (since 2025-03-31). So:

- **The opening is readable at frame 0.** The hook (scene 0) is on screen, fully legible, in the very first frame;
  its motion only settles (remotion/src/ui.tsx `Opening`). `opening_ink()` checks a render's frame 0 for the QA.
- **The voice starts at once.** Leading silence on the voice track is cut to at most LEAD_KEEP seconds
  (`props.mix_audio` trims the track); the word timings move by the same amount, so the captions and the scene
  anchors stay in sync (`lead_trim`, `shift`).
- **The ending is a format choice, `outro`:**
    card     the end card (logo, QR, link, CTA): the default, as before.
    overlay  no end card: the story's end scene is dropped, the last content scene stays to the end, and a compact
             chip with the QR, the link and the CTA slides into the safe area for its last seconds
             (remotion/src/outro.tsx). The tail after the last word is shorter: there is no card to read.
    loop     like overlay, and the last LOOP_SECONDS cross-fade into the hook's frame 0; the music keeps its steady
             level to the last frame (only a de-click fade), so the replay runs on without a seam.
"""
import re
import subprocess

from tt_shorts import speech

FPS = speech.FPS
OUTROS = ("card", "overlay", "loop")
DEFAULT_OUTRO = "card"
ABOUT = {
    "card": "the end card: logo, QR to the story, link and the call to action (as before)",
    "overlay": "no end card: a compact chip with the QR, link and CTA slides in over the last scene's final seconds",
    "loop": "no end card, the chip, and the last 0.5 s cross-fade into the hook's first frame: a seamless replay",
}
HOLD = {"card": speech.END_HOLD, "overlay": 1.0, "loop": 0.8}  # seconds after the last word
CHIP_SECONDS = 3.0  # the chip is on screen at least this long (it comes in with the end scene's words, or earlier)
LOOP_SECONDS = 0.5  # remotion/src/outro.tsx LOOP (frames) = this * FPS
LEAD_KEEP = 0.12  # at most this much silence before the first word
SILENCE_DB = -50  # quieter than this counts as silence at the start of the voice track
MUSIC_FADES = {"loop": (0.03, 0.03)}  # (in, out) seconds; loop: a de-click only, the level stays steady
MUSIC_FADE_DEFAULT = (1.2, 2.5)
# frame 0's hook band: the share of ink-coloured pixels it must have (light on a dark theme's canvas, dark on a
# light theme's: brand.json themes)
INK_BAND = (250, 1100)
INK_LEVEL = 160  # 0-255 luma; a dark canvas and its motif are near black, ink and muted text well above (a light
# theme's ink is below 255 - INK_LEVEL)
INK_SHARE = 0.02


# ---------------------------------------------------------------- the voice starts at once


def leading_silence(audio):
    """Seconds of silence at the start of an audio file (ffmpeg silencedetect), 0.0 when it starts with sound, None
    when it can't be measured."""
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(audio), "-af",
                            f"silencedetect=noise={SILENCE_DB}dB:d=0.05", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    start = re.search(r"silence_start: (-?[\d.]+)", r.stderr)
    if not start or float(start.group(1)) > 0.01:
        return 0.0
    end = re.search(r"silence_end: ([\d.]+)", r.stderr)
    return float(end.group(1)) if end else None  # silent to the end: nothing to trust


def lead_trim(words, silence=None, keep=LEAD_KEEP):
    """Seconds to cut from the start of the voice so at most `keep` seconds come before the speech. The speech starts
    at the earlier of the first word's timing and the measured silence; without a measurement nothing is cut."""
    if not words or silence is None:
        return 0.0
    lead = min(words[0]["start"], silence)
    return round(max(0.0, lead - keep), 3)


def shift(words, by):
    """Word timings `by` seconds earlier (the trimmed track): captions and anchors move with the voice."""
    if not by:
        return words
    return [{**w, "start": round(max(0.0, w["start"] - by), 3), "end": round(max(0.0, w["end"] - by), 3)} for w in words]


# ---------------------------------------------------------------- the ending


def shown_scenes(story, outro=DEFAULT_OUTRO):
    """The scenes a video shows (no voice needed): overlay and loop drop the story's end scene."""
    scenes = story["scenes"]
    drop = outro != "card" and len(scenes) > 1 and scenes[-1].get("type") == "end"
    return scenes[:-1] if drop else scenes


def plan(story, words, outro=DEFAULT_OUTRO):
    """-> (scenes, marks, chip): the scenes the video shows, their start frames plus the last frame (speech.scene_frames),
    and the frame the outro chip comes in (None for the card).

    overlay and loop drop the story's end scene: the scene before it runs to the end. The chip comes in where the end
    scene would have started (its words are the call to action), and at least CHIP_SECONDS before the end."""
    if outro not in OUTROS:
        raise ValueError(f"outro {outro!r} is not one of {', '.join(OUTROS)}")
    scenes = story["scenes"]
    shown = shown_scenes(story, outro)
    drop = len(shown) < len(scenes)
    marks = speech.scene_frames({**story, "scenes": shown}, words, hold=HOLD[outro])
    if outro == "card":
        return shown, marks, None
    latest = marks[-1] - round(CHIP_SECONDS * FPS)
    cue = latest
    if drop:
        after, t = 0, None
        for s in scenes[1:]:  # the same search as scene_frames, so a repeated phrase finds the end scene's words
            t, after = speech.anchor(words, s["at"], after)
        cue = round((t - 0.08) * FPS)
    return shown, marks, max(marks[-2] + round(0.5 * FPS), min(cue, latest))  # never before the last scene is in


def music_fades(outro):
    """(fade in, fade out) seconds of the music bed for an outro."""
    return MUSIC_FADES.get(outro, MUSIC_FADE_DEFAULT)


# ---------------------------------------------------------------- QA: the opening frame


def opening_ink(video, light=False):
    """The share (0..1) of ink-coloured pixels in frame 0's hook band (y INK_BAND), or None when ffmpeg can't read it.
    light: the video's theme is a light ground (brand.mode), so ink is the dark pixels."""
    top, bottom = INK_BAND
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf",
                            f"crop=iw:{bottom - top}:0:{top},format=gray", "-frames:v", "1", "-f", "rawvideo", "-"],
                           capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    raw = r.stdout
    if r.returncode != 0 or not raw:
        return None
    ink = bytes(range(0, 256 - INK_LEVEL)) if light else bytes(range(INK_LEVEL, 256))
    ground = len(raw.translate(None, ink))  # the bytes left once the ink ones are deleted
    return (len(raw) - ground) / len(raw)


def opening_problems(video, share=..., light=False):
    """QA messages about frame 0 (empty when the hook is readable there); `share` when opening_ink() already ran."""
    if share is ...:
        share = opening_ink(video, light)
    if share is None:
        return ["frame 0: could not be read (ffmpeg)"]
    if share < INK_SHARE:
        return [f"frame 0: the hook band (y {INK_BAND[0]}-{INK_BAND[1]}) is {share:.1%} ink, under {INK_SHARE:.0%}: "
                "the opening is not readable at frame 0, where a swipe decides"]
    return []
