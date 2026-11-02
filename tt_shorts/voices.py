"""Voice tones for Veasy videos (Gemini TTS). The shared presets are calm news tones. SiTech reads tech news in
`Charon` with an energetic delivery: that preset lives in brands/sitech (a pack's own "voices"), not here. The owner
picks by ear from the samples.

  python -m tt_shorts.voices                    # every preset reads the same sample text -> out/voices/<preset>.wav
  python -m tt_shorts.voices --story stories/24725.json --only anchor,warm

The delivery goes in speech_metadata.style (speech.gemini_speak), never in the spoken text. SHORTS_VOICE picks
the channel's default preset; `family` picks the brand pack's preset for the story's category family.
"""
import argparse
import json
import os
import pathlib

# Gemini 3.8 guidance (the owner's research, docs 2026-10): keep the style short or empty, put no directions in the
# spoken text, try an empty style first. The narration guide adds: weak word stress, focus by phrase, statements
# settle low, ~4.5-5 syllables per second with pauses. Voices: Google's descriptors (Informative, Firm, Clear, Warm,
# Even); none is SiTech's Charon.
NEWS = ("Natural contemporary Georgian news delivery. Calm and clear, weak word stress, focus on the key fact of "
        "each sentence, statements settle low. Brief pauses between sentences. Not theatrical, not promotional.")
PRESETS = {
    "plain": {"label": "ნეიტრალური (სტილის გარეშე)", "voice": "Rasalgethi", "style": ""},
    "anchor": {"label": "საინფორმაციო წამყვანი", "voice": "Rasalgethi", "style": NEWS},
    "firm": {"label": "მტკიცე", "voice": "Kore", "style": NEWS},
    "clear": {"label": "მკაფიო", "voice": "Iapetus", "style": NEWS},
    "warm": {"label": "თბილი მთხრობელი", "voice": "Sulafat",
             "style": "Warm, conversational Georgian, like explaining today's news to one friend. Natural phrasing, "
                      "weak word stress, relaxed pauses. Friendly but exact with facts."},
    "documentary": {"label": "დოკუმენტური", "voice": "Gacrux",
                    "style": "Measured, serious Georgian narration for hard news. Steady pace, calm pauses, statements "
                             "settle low. Respectful, never dramatic."},
}
# The tones the owner liked by ear for tbilisi.today (2026-11-01: plain, anchor, warm, clear; not firm or
# documentary). Which tone a family gets is the brand pack's voice_by_family (brands/_ka: hard news reads as the
# anchor, people's news warm, numbers and tech clear, sports plain). A pack may add presets of its own ("voices"):
# SiTech's Charon lives in brands/sitech, so only SiTech videos can use it.
APPROVED = ("plain", "anchor", "warm", "clear")
SAMPLE = ("ვარკეთილსა და ვაზისუბანში 2 ნოემბერს გაზი შეწყდება. „თბილისი ენერჯის“ ცნობით, მიწოდება "
          "6400 აბონენტს დროებით შეუწყდება. ამ ამბავს ოთხი მედია აშუქებს. დეტალები tbilisi.today-ზე.")


def all_presets(b=None):
    """The shared presets plus the brand pack's own (a pack's preset of the same name wins)."""
    return {**PRESETS, **((b or {}).get("voices") or {})}


def known():
    """Every preset name any pack can use (formats are validated against this; the pack decides at render)."""
    from tt_shorts import brand
    names = set(PRESETS)
    for n in brand.names():
        names |= set(brand.load(n).get("voices") or {})
    return names


def preset(name=None, category=None, b=None):
    """The preset to read a story with: its own, else SHORTS_VOICE; "family" (the default) picks by the category's
    family in the brand pack."""
    from tt_shorts import brand, meta
    b = b if isinstance(b, dict) else brand.load(b)
    name = name or os.environ.get("SHORTS_VOICE", "family")
    if name == "family":
        name = b["voice_by_family"][meta.family(category or "", b)]
    every = all_presets(b)
    if name not in every:
        raise ValueError(f"voice preset {name!r} is not available to brand {b['name']} (has: {', '.join(every)})")
    return {"name": name, **every[name]}


def main():
    from tt_shorts import normalize_ka, speech
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", help="read this story's narration instead of the sample text")
    ap.add_argument("--only", help="comma-separated presets")
    ap.add_argument("--out", default=str(speech.ROOT / "out" / "voices"))
    a = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set: the samples need the Gemini TTS API")
    text, say = SAMPLE, None
    if a.story:
        story = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
        text, say = story["narration"], story.get("say")
    spoken = normalize_ka.speech(text, say)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in (a.only.split(",") if a.only else PRESETS):
        wav = out / f"{name}.wav"
        speech.gemini_speak(spoken, wav, None, preset(name), slug=f"voice-sample-{name}")
        print(f"{name:12} {PRESETS[name]['voice']:8} {PRESETS[name]['label']} -> {wav}")


if __name__ == "__main__":
    main()
