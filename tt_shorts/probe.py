"""The layout probe: every text block of a render reports where it really is, and code judges it like a person would.

Fifty videos a day go out without a human looking (ROADMAP D13). So, for each scene at its settled frame (the
entrances done, the exit not begun), the composition measures every text it draws (remotion/src/Probe.tsx, one
console line `VEASY_PROBE {...}` per frame) and remotion/probe.mjs collects the lines in one browser, with the
bundle built once per version of remotion/src. rules() then checks the boxes against the frame's bands:

    band      scene text inside the scene band, SCENE_TOP..SCENE_BOTTOM (248..1380)
    rail      below y=1100 nothing right of x=940 (the platforms' like/share rail): scene text and captions
    captions  caption text ends at CAPTION_BOTTOM (1552)
    frame     no text outside the 1080x1920 frame
    overflow  no text past its box (an ancestor whose content is wider or taller than it: scrollWidth > clientWidth)
    glyph     every character is in the brand font (a missing glyph shows as tofu or another font), checked
              against the cmap of the very woff2 the render uses
    font      the text is set in the pack's family, that weight loaded, and the frame was laid out after the font
              was in (text sized by measuring it would otherwise keep a fallback font's sizes)
    size      no text shrunk below the region's minimum (a long line squeezed by fitSize, a drawing's tiny label)
    contrast  every text readable on what is really under it (a theme can put dark on dark or light on light): the
              text's color (its alpha times its opacity) against its ground, every element the page paints under the
              middle of its first line below the text's own element (document.elementsFromPoint: backgrounds, SVG
              fills, siblings included; what covers the text, a wipe passing over it, is not its ground),
              composited over the canvas. At least CONTRAST["text"] (3:1) for every fully shown text, and
              CONTRAST["small"] (4.5:1) for small regular text (under SMALL_PX and lighter than 600). Over a
              picture (img, video: a scene's media) the ground is unknown, so it is bounded: the layers above the
              picture (its scrim) over black and over white ("ground", "ground2"), and the worse one counts,
              against 3:1 for any size (a bound, not the picture: the small-text floor would fail every quiet
              credit under a scrim for a picture that is never pure white). An
              ornament (data-probe-decor: the quote scene's giant „, faint by design) is not judged.

The header and the footer are the brand's chrome: they are checked for frame, overflow, glyph, font and size, not
for the rail (the footer's pack line sits bottom right by design). The ticker scrolls out of the frame by design
and is not measured. The constants come from remotion/src/brand.ts, so the probe and the composition can't drift.

    python -m tt_shorts.engine probe stories/24725.json [--look all|editorial,kinetic] [--engine silent]

render_story probes every video before it renders (VEASY_PROBE=0 turns it off); a problem holds the job.
A region is what an element's nearest data-probe attribute says (scene, card, captions, header, footer, ticker).
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import time
import unicodedata

from tt_shorts import store

ROOT = pathlib.Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
BRAND_TS = REMOTION / "src" / "brand.ts"
FPS = 30
EXIT = 7  # frames a scene takes to leave (remotion/src/NewsShort.tsx)
TOL = 2.0  # px: sub-pixel rounding and antialiasing
RAIL_Y = 1100  # below this, nothing right of RAIL_X (CLAUDE.md: the safe zone)
# The smallest effective size (font size x any scale) per region, px. The writer's drawing labels may be 26 at the
# drawing's own scale (art.GUIDE), which a card shrinks to ~24; captions.MIN_SIZE is 44; the footer's link shrinks
# to 22 for a long slug (NewsShort Footer).
MIN_PX = {"scene": 24, "card": 26, "captions": 40, "header": 26, "footer": 22, "other": 24}
CHROME = ("header", "footer")
WEIGHTS = ("400", "500", "600", "700")  # brand.FONT_WEIGHTS: every pack ships the four
RULES = ("band", "rail", "captions", "frame", "overflow", "glyph", "font", "size", "contrast")
CONTRAST = {"text": 3.0, "small": 4.5}  # WCAG ratios: large/bold text, and small regular text
SMALL_PX = 32


def constants(path=BRAND_TS):
    """The layout bands as remotion/src/brand.ts declares them: {W, H, SIDE, SCENE_TOP, ...} (+ RAIL_Y)."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    out = {k: int(v) for k, v in re.findall(r"export const ([A-Z_]+) = (\d+);", text)}
    out.setdefault("RAIL_Y", RAIL_Y)
    return out


C = constants()


def settled(scenes):
    """Each scene's settled frame: just before its exit starts (the last scene has no exit: its last frame)."""
    out = []
    for i, s in enumerate(scenes):
        last = s["from"] + s["duration"] - 1
        out.append(last if i == len(scenes) - 1 else max(s["from"] + min(s["duration"] - 1, 12), last - EXIT - 1))
    return out


# ---------------------------------------------------------------- the rules (pure: unit-tested on synthetic boxes)


def _family(css):
    return (css or "").split(",")[0].strip().strip("\"'")


def _weight(w):
    w = {"normal": "400", "bold": "700"}.get(str(w), str(w))
    try:
        n = int(float(w))
    except ValueError:
        return "400"
    return str(min((400, 500, 600, 700), key=lambda x: abs(x - n)))


def missing_glyphs(text, cmap):
    """Characters of `text` the font has no glyph for (spaces and invisible format characters aside)."""
    out = []
    for ch in text:
        if ch.isspace() or unicodedata.category(ch) in ("Cc", "Cf", "Zs", "Zl", "Zp"):
            continue
        if ord(ch) not in cmap and ch not in out:
            out.append(ch)
    return out


def _quote(text, n=40):
    t = " ".join(text.split())
    return f"„{t[:n]}{'…' if len(t) > n else ''}“"


def text_contrast(t):
    """(ratio, color, ground) of one probed text, or None when the probe gave no color or no ground (a picture)."""
    from tt_shorts import brand
    color, ground = t.get("color"), t.get("ground")
    if isinstance(color, str):  # the HyperFrames probe's computed CSS color ("rgb(1, 2, 3)"), times its opacity
        c = brand.rgba(color)
        color = (*c[:3], c[3] * (t.get("opacity") or 1)) if c else None
    if not color or not ground or len(color) < 3 or len(ground) < 3:
        return None
    fg = (*color[:3], color[3] if len(color) > 3 else 1.0)
    grounds = [(*g[:3], 1.0) for g in (ground, t.get("ground2")) if g and len(g) >= 3]  # ground2: over a picture
    return min((brand.contrast(fg, bg), fg, bg) for bg in grounds)


def _css(c):
    return "#" + "".join(f"{round(v):02X}" for v in c[:3]) + (f" at {c[3]:.2f}" if len(c) > 3 and c[3] < 1 else "")


def rules(report, cmaps=None, c=None):
    """One frame's probe report -> [{rule, region, text, detail}]. cmaps: {weight: set of code points} of the
    brand font (glyph rule); without it the glyph rule is skipped."""
    c = c or C
    W, H = c["W"], c["H"]
    out = []

    def bad(rule, t, detail):
        out.append({"rule": rule, "region": t.get("region"), "text": t.get("text", ""), "detail": detail})

    fonts = report.get("fonts") or {}
    early = report.get("fontsAtRender")
    if early is not None and any(early.get(w) != "loaded" for w in WEIGHTS):
        late = ", ".join(w for w in WEIGHTS if early.get(w) != "loaded")
        out.append({"rule": "font", "region": "page", "text": "",
                    "detail": f"the frame was laid out before the brand font's weight {late} loaded: text sized by "
                              "measuring it got a fallback font's sizes (remotion/src/fonts.tsx holds the layout)"})
    for t in report.get("texts") or []:
        x, y, w, h = t["box"]
        right, bottom = x + w, y + h
        region = t.get("region") or "other"
        q = _quote(t.get("text", ""))
        if region == "scene" and (y < c["SCENE_TOP"] - TOL or bottom > c["SCENE_BOTTOM"] + TOL):
            edge = f"ends at y={bottom:.0f}, below" if bottom > c["SCENE_BOTTOM"] + TOL else f"starts at y={y:.0f}, above"
            bad("band", t, f"{q} {edge} the scene band ({c['SCENE_TOP']}-{c['SCENE_BOTTOM']})")
        if region not in CHROME and bottom > c["RAIL_Y"] + TOL and right > c["RAIL_X"] + TOL:
            bad("rail", t, f"{q} reaches x={right:.0f} below y={c['RAIL_Y']} (the like/share rail starts at "
                           f"x={c['RAIL_X']})")
        if region == "captions" and bottom > c["CAPTION_BOTTOM"] + TOL:
            bad("captions", t, f"{q} ends at y={bottom:.0f}, below the captions' band ({c['CAPTION_BOTTOM']})")
        if x < -TOL or y < -TOL or right > W + TOL or bottom > H + TOL:
            bad("frame", t, f"{q} is outside the {W}x{H} frame (box {x:.0f},{y:.0f} to {right:.0f},{bottom:.0f})")
        o = t.get("overflow")
        if o and not t.get("clipOk"):
            size = t.get("size") or 0
            how = "is cut off by" if o.get("clipped") else "runs past"
            if o.get("x", 0) > TOL:
                bad("overflow", t, f"{q} {how} its box ({o.get('xIn') or 'its container'}) by {o['x']:.0f} px across")
            elif o.get("y", 0) > max(TOL, 0.25 * size):
                bad("overflow", t, f"{q} {how} its box ({o.get('yIn') or 'its container'}) by {o['y']:.0f} px down")
        weight = _weight(t.get("weight"))
        fam = _family(t.get("family"))
        if fam != "Brand":
            bad("font", t, f"{q} is set in {fam or 'no family'}, not the brand's font")
        elif fonts and fonts.get(weight) != "loaded":
            bad("font", t, f"{q}: the brand font's weight {weight} is {fonts.get(weight) or 'missing'}, the browser "
                           "draws another font")
        if cmaps and fam == "Brand":
            gone = missing_glyphs(t.get("text", ""), cmaps.get(weight) or cmaps.get("700") or set())
            if gone:
                bad("glyph", t, f"{q} has characters the brand font lacks: "
                                + " ".join(f"{ch} (U+{ord(ch):04X})" for ch in gone))
        floor = MIN_PX.get(region, MIN_PX["other"])
        if (t.get("opacity") or 1) >= 0.9 and (t.get("size") or 99) < floor - 0.5:
            bad("size", t, f"{q} is {t['size']:.0f} px, under the {floor} px minimum for {region} text")
        judged = text_contrast(t) if (t.get("opacity") or 1) >= 0.9 and not t.get("decor") else None
        if judged:
            ratio, fg, bg = judged
            # over a picture the ground is a worst-case bound (a pure black or white picture), so 3:1 is the floor
            small = (t.get("size") or 99) < SMALL_PX and int(_weight(t.get("weight"))) < 600 and not t.get("ground2")
            need = CONTRAST["small" if small else "text"]
            if ratio < need - 1e-6:
                bad("contrast", t, f"{q} is {_css(fg)} on {_css(bg)}{' (over a picture, its worst case)' if t.get('ground2') else ''}: "
                                   f"{ratio:.2f}:1, under {need:g}:1{' for small text' if small else ''} "
                                   "(dark on dark or light on light)")
    return out


def problems(reports, cmaps=None, c=None, prefix=""):
    """Probe reports of one render -> (problem strings, issue dicts). The same issue on the chrome in every frame
    is reported once, with the first frame."""
    seen, strings, issues = set(), [], []
    for rep in reports:
        where = f"scene {rep.get('scene')} ({rep.get('type')}) frame {rep.get('frame')}"
        for it in rules(rep, cmaps, c):
            key = (it["rule"], it["region"], it["text"], it["detail"] if it["region"] in CHROME else rep.get("scene"))
            if key in seen:
                continue
            seen.add(key)
            it = {**it, "scene": rep.get("scene"), "type": rep.get("type"), "frame": rep.get("frame")}
            issues.append(it)
            on = f"{it['region']} frame {rep.get('frame')}" if it["region"] in CHROME + ("captions",) else where
            strings.append(f"probe {it['rule']}: {prefix}{on}: {it['detail']}")
    return strings, issues


# ---------------------------------------------------------------- running it


class ProbeError(RuntimeError):
    pass


def cmaps_for(public):
    """{weight: code points} of the brand font copied into a render's public dir (props.build)."""
    from fontTools.ttLib import TTFont
    out = {}
    for f in sorted((pathlib.Path(public) / "fonts").glob("brand-*.woff2")):
        out[f.stem.split("-")[-1]] = set(TTFont(str(f)).getBestCmap())
    return out


def run_jobs(jobs, timeout=900):
    """Render probes (and stills when a job has "out") for several jobs in one browser (remotion/probe.mjs).
    jobs: [{"props", "public", "frames", "out"?, "name"?, "probe"?}] -> (rows per job, {"seconds", "bundle", ...})."""
    from tt_shorts import props as props_mod
    spec = {"cache": str(store.bundle_dir()), "browser": props_mod.chrome(), "jobs": jobs}
    try:
        r = subprocess.run(["node", "probe.mjs"], cwd=REMOTION, input=json.dumps(spec), capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ProbeError(f"the probe timed out after {timeout}s")
    except OSError as e:
        raise ProbeError(f"the probe could not start node: {e}")
    rows = []
    for line in r.stdout.splitlines():
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    done = next((x for x in rows if x.get("done")), None)
    fatal = next((x["fatal"] for x in rows if x.get("fatal")), None)
    if fatal or not done:
        raise ProbeError((fatal or r.stderr or "no result")[-1500:])
    per = [[] for _ in jobs]
    for x in rows:
        if "job" in x:
            per[x["job"]].append(x)
    return per, done


def judge(rows, public, frames, prefix=""):
    """One job's rows -> {"problems", "issues", "frames", "texts"}: a frame with no report is itself a problem."""
    errors = [x["error"] for x in rows if x.get("error")]
    reports = [x["probe"] for x in rows if x.get("probe")]
    strings, issues = problems(reports, cmaps_for(public), prefix=prefix)
    got = {r["frame"] for r in reports}
    lost = [f for f in frames if f not in got]
    if errors:
        strings.append(f"probe error: {prefix}{errors[0].splitlines()[0][:300]}")
    elif lost:
        strings.append(f"probe error: {prefix}no layout report for frames {lost} (the composition did not answer)")
    return {"problems": strings, "issues": issues, "frames": frames, "texts": sum(len(r["texts"]) for r in reports),
            "files": [x["file"] for x in rows if x.get("file")]}


def check_work(work, p, out=None):
    """Probe a built render (props.build's work dir and props) at each scene's settled frame."""
    t0 = time.time()
    frames = settled(p["scenes"])
    job = {"props": str(pathlib.Path(work) / "props.json"), "public": str(pathlib.Path(work) / "public"),
           "frames": frames, "out": str(out) if out else None, "name": p["variant"]}
    per, done = run_jobs([job])
    result = judge(per[0], job["public"], frames)
    result["seconds"] = round(time.time() - t0, 1)
    shutil.rmtree(pathlib.Path(work) / "probe-serve", ignore_errors=True)
    return result


def enabled():
    return os.environ.get("VEASY_PROBE", "1") != "0"


def looks(choice, story):
    """--look: auto (the story's own look), all, or a comma-separated list."""
    from tt_shorts import brand, meta
    if choice in (None, "", "auto"):
        return [meta.variant_for(story.get("category", ""), brand.of(story))]
    if choice == "all":
        return list(brand.LOOKS)
    out = [x.strip() for x in choice.split(",") if x.strip()]
    bad = [x for x in out if x not in brand.LOOKS]
    if bad:
        raise ValueError(f"unknown look {bad[0]!r}; use auto, all or {', '.join(brand.LOOKS)}")
    return out


def story(story_path, fmt, look="auto", engine="silent", stills=None):
    """`engine probe`: one story in one or more looks, every scene at its settled frame, in one browser."""
    from tt_shorts import props, speech
    t0 = time.time()
    data = json.loads(pathlib.Path(story_path).read_text(encoding="utf-8"))
    chosen = looks(look, data)
    tone = None if fmt["voice"] == "family" else fmt["voice"]
    jobs, built = [], []
    for lk in chosen:
        work, p = props.build(str(story_path), lk, engine, tone, speech.EDGE_VOICES["eka"], fmt["platform"],
                              caption_design=fmt["captions"], music="off", transition=fmt["transition"],
                              theme=fmt.get("theme"))
        frames = settled(p["scenes"])
        jobs.append({"props": str(work / "props.json"), "public": str(work / "public"), "frames": frames,
                     "out": str(pathlib.Path(stills).resolve()) if stills else None,
                     "name": f"{store.safe(p['id'])}-{lk}" + (f"-{p['theme']}" if fmt.get("theme") not in
                                                                   (None, "default") else "")})
        built.append((lk, work, p, frames))
    per, done = run_jobs(jobs)
    result, found = {}, []
    for (lk, work, p, frames), rows in zip(built, per):
        r = judge(rows, work / "public", frames, prefix=f"{lk}: " if len(chosen) > 1 else "")
        result[lk] = {"problems": r["problems"], "issues": r["issues"], "frames": frames, "texts": r["texts"],
                      "scenes": [s["type"] for s in p["scenes"]], "stills": r["files"]}
        found += r["problems"]
        shutil.rmtree(work / "probe-serve", ignore_errors=True)
    return {"story": str(pathlib.Path(story_path).resolve()), "engine": engine, "looks": result, "problems": found,
            "seconds": round(time.time() - t0, 1), "bundle_built": done.get("built")}
