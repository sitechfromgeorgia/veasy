"""Ten blind pairs (docs/research/thread-object-evidence): a story as the kit draws it against the same facts built on an
object, in one sheet per pair, the sides shuffled, the key in a separate file. No voice, no writer: silent timings,
stills from one browser (remotion/probe.mjs).

    python tools/thread_pairs.py [--out docs/research/thread-object-evidence] [--only explainer-inflation] [--check]

--check builds the object's side only and prints what the layout probe says, in every look.
"""
import argparse
import json
import pathlib
import random
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from tt_shorts import engine, probe, props, speech  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "research" / "thread-object-evidence"
FRAMES = 6  # stills a side
THUMB = (270, 480)
GAP = 12
SHUFFLE_SEED = 20261107


def threaded(pair):
    """The object's side of a pair: the story with its concept, its one sentence and its state scene."""
    s = json.loads((ROOT / "stories" / f"{pair['story']}.json").read_text(encoding="utf-8"))
    s["id"] = f"{pair['story']}-thread"
    s["program"] = "explainer"
    s["concept"] = {**pair["concept"], "rejected": [], "roll": {"seed": "pair", "kind": "agent"}}
    if pair.get("scenes"):
        s["scenes"], s["narration"] = pair["scenes"], pair["narration"]
        return s
    if pair.get("scene"):
        s["scenes"].insert(pair["scene"]["index"], pair["scene"]["scene"])
    st = pair["state"]
    k = next(i for i, x in enumerate(s["scenes"]) if x.get("at") == st["before"])
    s["scenes"].insert(k, {"type": "state", **{key: st[key] for key in ("at", "kicker", "headline", "was", "now")}})
    s["narration"] = s["narration"].replace(st["before"], f"{st['say']} {st['before']}", 1)
    return s


def kit(pair):
    s = json.loads((ROOT / "stories" / f"{pair['story']}.json").read_text(encoding="utf-8"))
    s["id"] = f"{pair['story']}-kit"
    return s


def build(story, folder, look, style):
    path = folder / f"{story['id']}.json"
    path.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
    return props.build(str(path), look, "silent", None, speech.EDGE_VOICES["eka"], "shorts", caption_design="page",
                       music="off", transition="auto", style=style)


def picks(scenes):
    """At most FRAMES settled frames, spread over the film, the end card left out."""
    shown = [(i, f) for i, (s, f) in enumerate(zip(scenes, probe.settled(scenes))) if s["type"] not in ("end", "sources")]
    if len(shown) <= FRAMES:
        return [f for _, f in shown]
    step = (len(shown) - 1) / (FRAMES - 1)
    return [shown[round(k * step)][1] for k in range(FRAMES)]


def sheet(top, bottom, out):
    w, h = THUMB
    rows = (top, bottom)
    canvas = Image.new("RGB", (FRAMES * (w + GAP) + GAP, 2 * (h + GAP) + GAP), (72, 72, 72))
    for r, files in enumerate(rows):
        for c, f in enumerate(files):
            canvas.paste(Image.open(f).convert("RGB").resize(THUMB), (GAP + c * (w + GAP), GAP + r * (h + GAP)))
    canvas.save(out, quality=78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EVIDENCE))
    ap.add_argument("--only")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    pairs = json.loads((EVIDENCE / "pairs.json").read_text(encoding="utf-8"))["pairs"]
    pairs = [p for p in pairs if not a.only or p["story"] == a.only]
    with tempfile.TemporaryDirectory() as tmp:
        folder = pathlib.Path(tmp)
        if a.check:
            return check(pairs, folder)
        jobs, sides = [], []
        for n, pair in enumerate(pairs):
            for side, story, look in (("kit", kit(pair), "editorial"), ("object", threaded(pair), "editorial")):
                style = {"hook": "stack", "motif": "dots", "enter": "rise"}
                work, p = build(story, folder, look, style)
                frames = picks(p["scenes"])
                jobs.append({"props": str(work / "props.json"), "public": str(work / "public"), "frames": frames,
                             "out": str(folder / "stills"), "name": story["id"]})
                sides.append({"pair": n, "side": side, "story": pair["story"], "scenes": [s["type"] for s in p["scenes"]],
                              "transition": p["transition"], "thread": [i for i, s in enumerate(p["scenes"]) if s.get("thread")],
                              "warnings": p.get("threadWarnings")})
        per, _ = probe.run_jobs(jobs)
        out = pathlib.Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        key, rng = {}, random.Random(SHUFFLE_SEED)
        for n, pair in enumerate(pairs):
            files = {x["side"]: [r["file"] for r in per[i] if r.get("file")] for i, x in enumerate(sides) if x["pair"] == n}
            first = rng.choice(("kit", "object"))
            other = "object" if first == "kit" else "kit"
            name = f"pair-{n + 1:02d}.jpg"
            sheet(files[first], files[other], out / name)
            key[name] = {"story": pair["story"], "top": first, "bottom": other}
        (out / "KEY-do-not-open-before-choosing.json").write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n",
                                                                  encoding="utf-8")
        (out / "sides.json").write_text(json.dumps(sides, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"sheets": len(key), "out": str(out)}))
        shutil.rmtree(folder / "stills", ignore_errors=True)


def check(pairs, folder):
    jobs, built = [], []
    for pair in pairs:
        story = threaded(pair)
        print(story["id"], engine.check_story(story)[:4])
        for look in ("editorial", "kinetic", "cards"):
            work, p = build(story, folder, look, None)
            frames = probe.settled(p["scenes"])
            jobs.append({"props": str(work / "props.json"), "public": str(work / "public"), "frames": frames,
                         "out": None, "name": f"{story['id']}-{look}"})
            built.append((story["id"], look, p, work, frames))
    per, _ = probe.run_jobs(jobs)
    bad = 0
    for (sid, look, p, work, frames), rows in zip(built, per):
        r = probe.judge(rows, work / "public", frames)
        seats = [s["type"] for s in p["scenes"] if s.get("thread")]
        print(sid, look, p["transition"], "seats:", seats, "warn:", p.get("threadWarnings"))
        for x in r["problems"]:
            bad += 1
            print("   ", x[:170])
    print("problems:", bad)
    tall = {}
    for (sid, look, p, work, frames), rows in zip(built, per):
        for s, row in zip(p["scenes"], rows):
            boxes = [t["box"] for t in (row.get("probe") or {}).get("texts") or [] if t.get("region") in ("scene", "card")]
            if boxes and s["type"] not in ("end", "where"):
                top = 248 + (48 if look == "cards" else 0)
                n = len(s.get("items") or s.get("lines") or [])
                key = (s["type"], "cards" if look == "cards" else "full", n)
                tall[key] = max(tall.get(key, 0), max(b[1] + b[3] for b in boxes) - top)
    for k in sorted(tall):
        print(k, round(tall[k]))


if __name__ == "__main__":
    main()
