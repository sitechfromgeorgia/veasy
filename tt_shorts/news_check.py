"""News rules (N1-N6 in ka_style.md) for a story JSON, checked against the story's member articles.

Videos go out without a human review, so what code can see, code checks. Each problem names its rule and goes back
to the writer, like ka_check's K rules. `sources` is the list of member article texts (title + body).

  N1  no opinion: there is no "take" scene, and the narration has no evaluative words
  N2  numbers: every number in the narration and on screen is in at least one member article
  N3  quotes: a quote scene's text and every „…“ in the narration appear verbatim in a member article
  N4  no relative days (დღეს, გუშინ, ხვალ, ზეგ): a video is watched for days; the screen carries the date
  N5  sensitive stories are skipped, not written (sexual violence, children as victims, suicide)
  N6  the outlets and the date come from the data: the pipeline sets `sources` and `date` after the writer
      (not checked here; the writer's JSON never carries them)
"""
import re

SCENE_TYPES = {"hook", "stat", "timeline", "where", "who", "points", "quote", "sources", "end"}
RELATIVE_DAYS = ("დღეს", "გუშინ", "ხვალ", "ზეგ", "გუშინწინ")
# Words that judge instead of report (stems: Georgian adds case endings). Extend from the edits log.
EVALUATIVE = ("სკანდალურ", "შოკისმომგვრელ", "სამარცხვინო", "საოცარ", "გასაოცარ", "უპრეცედენტო", "საშინელ",
              "სენსაციურ", "ისტორიულ", "ბრწყინვალე", "კატასტროფულ", "აღმაშფოთებელ")
SENSITIVE = ("გაუპატიურ", "სექსუალურ ძალადობ", "სექსუალური ძალადობ", "თვითმკვლელ", "სუიციდ", "არასრულწლოვან",
             "ბავშვზე ძალადობ", "პედოფილ")
NUM = re.compile(r"\d+")


def flat(text):
    """Text for verbatim matching: one kind of quote, single spaces, no HTML entities."""
    text = text.replace("&bdquo;", "„").replace("&ldquo;", "“").replace("&quot;", '"')
    text = re.sub(r"[„“”\"«»]", '"', text)
    return re.sub(r"\s+", " ", text).strip()


def numbers(text):
    return set(NUM.findall(text))


def screen_text(story):
    """Every word the writer put on screen (sources and date come from the data, not the writer)."""
    out = []
    for s in story.get("scenes", []):
        for k, v in s.items():
            if k in ("type", "at"):
                continue
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, list):
                for it in v:
                    out += [x for x in (it.values() if isinstance(it, dict) else [it]) if isinstance(x, str)]
            elif isinstance(v, int) and k == "value":
                out.append(str(v))
    return " ".join(out)


def sensitive(texts):
    """N5: the stems found in a story's titles and texts; any hit means the story is skipped before writing."""
    joined = " ".join(texts).lower()
    return sorted({s for s in SENSITIVE if s in joined})


def problems(story, sources):
    out = []
    narration = story.get("narration", "")
    scenes = story.get("scenes", [])
    corpus = flat(" ".join(sources))
    corpus_numbers = numbers(corpus)

    for s in scenes:
        if s.get("type") not in SCENE_TYPES:
            out.append(f"N1: scene type {s.get('type')!r} is not allowed (no opinion or take scenes)")
    low = narration.lower()
    for w in EVALUATIVE:
        if w in low:
            out.append(f"N1: evaluative word in the narration: {w}… (report, don't judge)")

    seen = numbers(narration) | numbers(screen_text(story))
    for n in sorted(seen - corpus_numbers, key=lambda x: (len(x), x)):
        out.append(f"N2: number {n} is not in any source article")

    quotes = re.findall(r"„([^“”]+)[“”]", narration)
    quotes += [s["text"] for s in scenes if s.get("type") == "quote" and s.get("text")]
    for q in quotes:
        if flat(q) not in corpus:
            out.append(f"N3: quote is not verbatim in any source: „{q[:60]}“")

    for w in RELATIVE_DAYS:
        if re.search(rf"(?<![ა-ჰ]){w}(?![ა-ჰ])", narration + " " + screen_text(story)):
            out.append(f"N4: relative day „{w}“: name the date (2 ნოემბერს) or leave it out")

    hits = sensitive(sources + [narration])
    if hits:
        out.append(f"N5: sensitive story ({', '.join(hits)}): skip it")
    return out
