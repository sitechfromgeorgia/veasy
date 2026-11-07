"""The illustrator: the film's drawings (vignettes.py), drawn in a call of their own once the script is final.

The owner, 2026-11-07: a cheaper model with its own, better skill should draw them, and draw them well. The writer's
answer is about words and is capped (writer._call: 1800 tokens on OpenRouter); three SVGs in it crowd out the script,
and its editor's pass returns the whole JSON again. So the drawings leave that call. This one gets only what drawing
needs, and the parts that never change come first, so a provider that caches a prompt's start charges them once:

    the skill       GUIDE: one thing a viewer knows in a second, its parts planned on the canvas before the SVG,
                    simple shapes, motion that builds in order, and two finished examples (EXAMPLES, the library's
                    seeds without their labels)
    the scenes      wanted(): the hook first (the film's emblem, like a SiTech blog card), then the scenes whose words
                    the library has no drawing for, up to vignettes.MAX with the authors' own; only scenes with a seat.
                    Each comes with its part of the narration and the things its words name (icons.find), which a
                    model that reads Georgian poorly still understands, and what the library already draws elsewhere
    the checks      vignettes.own_problems on every drawing; one repair call with the exact problems for the ones that
                    failed; a drawing that still fails is left out (the library's or none). It never fails a video
    the model       VEASY_ILLUSTRATOR_MODEL, else the writer's, through the writer's provider (any OpenAI-format
                    server). VEASY_ILLUSTRATOR=0 turns the step off and the writer draws "art" itself again;
                    VEASY_WRITER_DRAW=0 turns every model drawing off

    python -m tt_shorts.engine vignettes stories/x.json           # free: what the library draws, what would be asked
    python -m tt_shorts.engine vignettes stories/x.json --draw    # one call (two with the repair): the story gets art
"""
import os

from tt_shorts import art, drawings, icons, news_check, thread, vignettes

ENV, MODEL_ENV = "VEASY_ILLUSTRATOR", "VEASY_ILLUSTRATOR_MODEL"
MAX_TOKENS = 6000  # three drawings of up to 4000 characters, their plans and the JSON around them
PART = 240  # characters of a scene's part of the narration in the prompt
EXAMPLES = ("gauge", "price-tag")  # short, clean seeds that move: the style, not the subject

GUIDE = """You draw the pictures of one short vertical news video, as SVG line art. Each picture shows what ONE part of
the video is about and stands under that part's text while the voice says it. The video is in Georgian; the pictures
have no words at all.

For each picture, in this order:
1. "subject": ONE concrete thing a viewer recognizes in a second, taken from that part's words: a shopping cart for food
   prices, a gas valve for a gas cut, a gauge with its needle for a rate against a target, a bus at a stop for a fare,
   a building with columns for a bank or a ministry. It may carry one small sign of the change the words say: an arrow
   up beside a price tag, a crack in a road, a needle past a mark. Never an abstract shape, a chart, a map, a flag, a
   logo, a face or a person.
2. "act": the ONE part that acts out what the words say, and how: the needle turns to its mark, the arrow climbs, the
   valve wheel turns shut, the bar grows, the car drives in. Optionally one part that keeps moving while the picture
   is on screen: wheels spin, a price tag sways, a flame breathes, a boat floats. This is a video: nothing is still.
3. "parts": the 4-8 parts you will draw, biggest first, each with its place on the 952x640 canvas, like
   "body: rounded rect x 220-730 y 160-520".
4. "svg": the SVG fragment (no <svg> tag) that draws exactly those parts.

The SVG (code checks every rule; a picture that fails is thrown away):
- Canvas 0 0 952 640. The thing is big: at least 60% of the canvas wide or high, centred near (476, 330).
- Line art: fill "none" and a stroke on almost everything, stroke-width 6-8 for outlines and 4-5 for details,
  round caps and joins. Rounded rects (rx 12-24) for bodies, devices and buildings. 8-30 elements, under 4000
  characters.
- Simple shapes: rect, circle, ellipse, line, polyline, polygon, and path with M L Q C A Z only.
- Colours: ONLY these words, in stroke and fill: INK (the main lines), MUTED (details), LINE (faint structure such as
  a floor line), CANVAS (a solid fill that hides the lines behind it), none, and ACCENT for ONE small dot only: a
  <circle> of r 8-24 filled ACCENT on the single focal part. Never ACCENT on a line, a shape or a fill.
- No <text>: no letters, no numbers, no labels, no currency signs.
- Motion: put the parts in <g> groups with class "s" (the line draws itself), "r" (rises in) or "p" (pops in) and
  style "--d:0.4s". At least 3 groups with different delays: the body first (0.2-0.6s), then the details
  (0.8-1.4s), the act and the accent dot last (1.4-2.2s). The act is a group with class "t" (turns in from
  "--turn:-60" degrees around "--at:x,y", its pivot: a needle's hub, a wheel's centre), "m" (moves in from
  "--from:0,120", dx,dy in px) or "g" (grows from its foot). It plays when the voice says the key words. A part
  that keeps moving adds to its style "--spin:90" (degrees a second, around --at), "--swing:6" (sways that many
  degrees, around --at: where it hangs), "--bob:10" (floats that many px) or "--pulse:1" (breathes). Example:
  <g class="t" style="--d:1.4s;--turn:-70;--at:476,470"><path d="M476 470 L518 234" stroke="INK" stroke-width="8"/></g>
- A different thing for each part: never the same thing twice in one video, nor one the library already draws.

Two finished pictures in this style (from the library; yours show the video's own things):"""

ASK = """Answer with JSON only:
{"drawings": [{"scene": 0, "subject": "...", "act": "...", "parts": ["..."], "svg": "..."}]}"""
NO_ACT = ("nothing in it moves: give ONE part an act (class t, m or g) that does what this part's words say, and "
          "maybe one loop (--spin, --swing, --bob or --pulse)")


def on():
    """Whether the step runs: not when VEASY_ILLUSTRATOR=0 or the writer may not draw at all (VEASY_WRITER_DRAW=0)."""
    from tt_shorts import writer
    return os.environ.get(ENV, "1") != "0" and writer.drawing()


def model():
    from tt_shorts import writer
    return os.environ.get(MODEL_ENV) or writer.MODEL


def examples():
    """The fixed examples, without labels: [(about, svg)]. A seed that is gone is skipped."""
    seeds = {s["name"]: s for s in drawings.seeds()}
    return [(seeds[n].get("about") or n, thread._strip(seeds[n]["svg"])) for n in EXAMPLES if n in seeds]


def wanted(story, look="editorial"):
    """The scenes to ask for, in scene order: the hook first, then the scenes the library draws nothing for, up to
    vignettes.MAX with the scenes' own drawings. [] when the story may get no drawing."""
    ok, _ = vignettes.eligible(story)
    scenes = story.get("scenes") or []
    if not ok:
        return []
    own = [i for i, s in enumerate(scenes) if isinstance(s.get("art"), str) and s.get("type") not in vignettes.SKIP]
    room = vignettes.MAX - len(own)
    seed = vignettes.seed_of(story)
    seats = [i for i, s in enumerate(scenes) if i not in own and not s.get("icon")
             and vignettes.seat_for(s, i, look, seed)]
    if room <= 0 or not seats:
        return []
    library = vignettes.plan(story, look=look)[0]
    first = [i for i in seats if scenes[i].get("type") == "hook"][:1]
    gaps = [i for i in seats if i not in library and i not in first]
    return sorted((first + gaps)[:room])


def _names(story, i):
    return ", ".join(icons.find(news_check.scene_part(story, i))[:4])


def prompt(story, asked, look="editorial"):
    """The whole prompt: the guide and the examples (the same for every video), then this video's parts."""
    scenes = story.get("scenes") or []
    library = vignettes.plan(story, look=look)[0]
    hook = next((s for s in scenes if s.get("type") == "hook"), {})
    lines = [GUIDE, ""]
    for about, svg in examples():
        lines += [f"subject: {about}", svg, ""]
    lines += [f"The video: category {story.get('category') or 'general'}; headline „{' '.join(hook.get('lines') or [])}“.",
              "Draw these parts:"]
    for i in asked:
        part = " ".join(news_check.scene_part(story, i).split())[:PART]
        names = _names(story, i)
        role = " (the opening: the video's emblem)" if scenes[i].get("type") == "hook" else ""
        lines.append(f"- scene {i}{role}: „{part}“" + (f" (its words name: {names})" if names else ""))
    taken = [f"{v['motif']} (scene {i})" for i, v in sorted(library.items()) if i not in asked and v.get("motif")]
    if taken:
        lines.append("Already drawn by the library, so draw other things: " + ", ".join(taken) + ".")
    lines += ["", ASK]
    return "\n".join(lines)


def _answers(text):
    """{scene: svg} from the model's answer; {} when it isn't the JSON asked for."""
    from tt_shorts import writer
    try:
        data = writer._object(text)
    except ValueError:
        return {}
    out = {}
    for d in data.get("drawings") or [] if isinstance(data, dict) else []:
        if isinstance(d, dict) and isinstance(d.get("scene"), int) and isinstance(d.get("svg"), str):
            out.setdefault(d["scene"], d["svg"])
    return out


def _judge(story, asked, got):
    """(passing {scene: svg}, failing {scene: [problems]}, still {scene: svg}) for the scenes asked. A drawing that
    passes every check but has no act goes back too (NO_ACT); `still` keeps it, to use if the repair is no better."""
    scenes = story.get("scenes") or []
    good, bad, still = {}, {}, {}
    for i in asked:
        svg = got.get(i)
        if svg is None:
            bad[i] = ["no drawing came back for this scene"]
            continue
        found = vignettes.own_problems({"type": scenes[i].get("type"), "art": svg})
        if found:
            bad[i] = found
        elif not art.acts(art.sanitize(svg)[0]):
            bad[i], still[i] = [NO_ACT], svg
        else:
            good[i] = svg
    return good, bad, still


def draw(story, look="editorial", call=None, repairs=1):
    """The story with its drawings -> (story, report). call(prompt) -> the model's text (default: the writer's provider
    with model()). Pure apart from the call; the story passed in is not changed. Never raises for a model's failure."""
    report = {"model": None, "asked": [], "drawn": [], "dropped": {}, "still": [], "calls": 0, "error": None}
    asked = wanted(story, look)
    report["asked"] = asked
    if not asked:
        return story, report
    if call is None:
        from tt_shorts import writer
        name = model()
        report["model"] = name

        def call(text):
            return writer._call(text, name, max_tokens=MAX_TOKENS)
    text = prompt(story, asked, look)
    good, bad, still = {}, {i: ["no answer"] for i in asked}, {}
    try:
        report["calls"] += 1
        good, bad, still = _judge(story, asked, _answers(call(text)))
        for _ in range(repairs):
            if not bad:
                break
            fix = (f"{text}\n\nThese pictures were thrown away by the checks. Draw only these scenes again, fixing every "
                   "problem:\n" + "\n".join(f"- scene {i}: " + "; ".join(p[:4]) for i, p in sorted(bad.items())))
            report["calls"] += 1
            more, bad, quiet = _judge(story, sorted(bad), _answers(call(fix)))
            good.update(more)
            still.update(quiet)
    except Exception as e:  # the model or the network: the film goes out with the library's drawings
        report["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    report["still"] = sorted(i for i in bad if i in still)  # no act after the repair: kept, the push-in moves it
    for i in report["still"]:
        good[i] = still[i]
        del bad[i]
    report["drawn"] = sorted(good)
    report["dropped"] = {i: p for i, p in sorted(bad.items())}
    if not good:
        return story, report
    scenes = [{**s, "art": good[i]} if i in good else s for i, s in enumerate(story.get("scenes") or [])]
    return {**story, "scenes": scenes}, report


def options():
    """What `engine options` shows an agent."""
    return {"about": "the film's drawings in a call of their own after the script (illustrator.py): the hook's emblem "
                     "and the scenes the library has nothing for, checked, one repair, never fails a video",
            "on": on(), "model": model(), "env": {"off": f"{ENV}=0", "model": MODEL_ENV},
            "examples": list(EXAMPLES)}
