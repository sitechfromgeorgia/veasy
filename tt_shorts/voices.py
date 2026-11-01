"""Voice tones for tbilisi.today Shorts (Gemini TTS). Not SiTech's: SiTech reads tech news in `Charon` with an
energetic delivery; a news channel needs calmer, more trustworthy tones. The owner picks by ear from the samples.

  python -m tt_shorts.voices                    # every preset reads the same sample text -> out/voices/<preset>.wav
  python -m tt_shorts.voices --story stories/24725.json --only anchor,warm

The delivery goes in speech_metadata.style (render.gemini_speak), never in the spoken text. SHORTS_VOICE picks
the channel's default preset; `family` sets one per category family (render picks it when the story has none).
"""
import argparse
import json
import os
import pathlib

PRESETS = {
    "anchor": {"label": "საინფორმაციო წამყვანი", "voice": "Kore",
               "style": "A calm, authoritative Georgian evening-news anchor. Even, unhurried pace, clear diction, "
                        "short pauses between facts. Neutral and trustworthy: no excitement, no drama, no sales tone."},
    "warm": {"label": "თბილი მთხრობელი", "voice": "Sulafat",
             "style": "A warm Georgian storyteller explaining today's news to a friend. Conversational and natural, "
                      "gentle emphasis on what matters to people, relaxed pauses. Friendly but never casual about facts."},
    "brisk": {"label": "დინამიკური", "voice": "Puck",
              "style": "A young Georgian social-media news host. Brisk, upbeat, energetic pace with crisp phrasing, "
                       "but grounded and factual: never sensational, never shouting, no hype words."},
    "documentary": {"label": "დოკუმენტური", "voice": "Gacrux",
                    "style": "A low, measured Georgian documentary narrator. Serious, steady and deliberate, with weight "
                             "on names and numbers and calm pauses. Respectful tone for hard news."},
    "bright": {"label": "ნეიტრალური ნათელი", "voice": "Aoede",
               "style": "A light, clear Georgian news reader. Bright and articulate, medium pace, neutral and easy "
                        "to follow, like a morning news brief."},
}
# One option for the owner: a tone per category family (hard news reads serious, light news reads lighter).
BY_FAMILY = {"politics": "anchor", "crime": "documentary", "world": "anchor", "economy": "bright",
             "society": "warm", "sports": "brisk", "culture": "warm", "tech": "bright"}
SAMPLE = ("ვარკეთილსა და ვაზისუბანში 2 ნოემბერს გაზი შეწყდება. „თბილისი ენერჯის“ ცნობით, მიწოდება "
          "6400 აბონენტს დროებით შეუწყდება. ამ ამბავს ოთხი მედია აშუქებს. დეტალები tbilisi.today-ზე.")


def preset(name=None, category=None):
    """The preset to read a story with: its own, else SHORTS_VOICE, else by family when
    SHORTS_VOICE=family, else anchor."""
    from tt_shorts.templates import family
    name = name or os.environ.get("SHORTS_VOICE", "anchor")
    if name == "family":
        name = BY_FAMILY[family(category or "society")]
    return {"name": name, **PRESETS[name]}


def main():
    from tt_shorts import normalize_ka, render
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", help="read this story's narration instead of the sample text")
    ap.add_argument("--only", help="comma-separated presets")
    ap.add_argument("--out", default=str(render.ROOT / "out" / "voices"))
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
        render.gemini_speak(spoken, wav, None, preset(name), slug=f"voice-sample-{name}")
        print(f"{name:12} {PRESETS[name]['voice']:8} {PRESETS[name]['label']} -> {wav}")


if __name__ == "__main__":
    main()
