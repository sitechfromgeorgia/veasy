"""Voice tones for tbilisi.today Shorts (Gemini TTS). Not SiTech's: SiTech reads tech news in `Charon` with an
energetic delivery; a news channel needs calmer, more trustworthy tones. The owner picks by ear from the samples.

  python -m tt_shorts.voices                    # every preset reads the same sample text -> out/voices/<preset>.wav
  python -m tt_shorts.voices --story stories/24725.json --only anchor,warm

The delivery goes in speech_metadata.style (speech.gemini_speak), never in the spoken text. SHORTS_VOICE picks
the channel's default preset; `family` sets one per category family (render picks it when the story has none).
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
# One option for the owner: a tone per category family (hard news reads serious, light news reads lighter).
BY_FAMILY = {"politics": "anchor", "crime": "documentary", "world": "anchor", "economy": "clear",
             "society": "warm", "sports": "firm", "culture": "warm", "tech": "clear"}
SAMPLE = ("ვარკეთილსა და ვაზისუბანში 2 ნოემბერს გაზი შეწყდება. „თბილისი ენერჯის“ ცნობით, მიწოდება "
          "6400 აბონენტს დროებით შეუწყდება. ამ ამბავს ოთხი მედია აშუქებს. დეტალები tbilisi.today-ზე.")


def preset(name=None, category=None):
    """The preset to read a story with: its own, else SHORTS_VOICE, else by family when
    SHORTS_VOICE=family, else anchor."""
    from tt_shorts.meta import family
    name = name or os.environ.get("SHORTS_VOICE", "anchor")
    if name == "family":
        name = BY_FAMILY[family(category or "society")]
    return {"name": name, **PRESETS[name]}


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
