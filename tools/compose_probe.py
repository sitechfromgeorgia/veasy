"""The layout probe on a composed film (Veasy v2 phase 0): tt_shorts/probe.py's rules, unchanged, on a HyperFrames page.

    python tools/compose_probe.py out/compose/24835-sitech [--shots out/compose/probe]   # a built project

compose/probe.mjs serves the project with HyperFrames' runtime and vendored GSAP (any other request is refused and
reported), seeks each beat's settled time with the runtime's renderSeek and measures every text as
remotion/src/Probe.tsx does. probe.rules() then judges the boxes (band, rail, captions, frame, overflow, glyph against
the pack's woff2 cmap, font, size). One rule only a composed page needs is added here, for a pack whose brand.json
says "design.accent.never" holds "text": "accent", no text drawn in the accent (the Remotion engine's components keep
it by construction; an agent's scene could break it).
"""
import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tt_shorts import brand, probe  # noqa: E402

PROBE_JS = ROOT / "compose" / "probe.mjs"
# the accent's own character in the pack's wordmark (tbilisi.today's dot) is the brand's, not a text color
WORDMARK_ACCENT = {"."}


def settled(timing):
    """(label, seconds) of each beat once its entrance has landed: 0.7 s in, or just before the next beat."""
    beats, out = timing["beats"], []
    for i, b in enumerate(beats):
        nxt = beats[i + 1]["t"] if i + 1 < len(beats) else timing["duration"]
        out.append((b["id"], round(min(b["t"] + 0.7, nxt - 0.05), 2)))
    return out


def rgb(hex_color):
    h = hex_color.lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


def accent_text(report, accent):
    want = rgb(accent)
    return [{"rule": "accent", "region": t.get("region"), "text": t.get("text", ""),
             "detail": f"„{t.get('text', '')[:40]}“ is drawn in the accent {accent} (the accent is never text)"}
            for t in report.get("texts") or [] if t.get("color") == want and t.get("text", "").strip() not in WORDMARK_ACCENT]


def run(project, shots=None):
    project = pathlib.Path(project).resolve()
    timing = json.loads((project / "timing.json").read_text(encoding="utf-8"))
    b = brand.load(timing["brand"])
    points = settled(timing)
    spec = {"project": str(project), "times": [t for _, t in points], "labels": [l for l, _ in points],
            "shots": str(pathlib.Path(shots).resolve()) if shots else None}
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["node", str(PROBE_JS)], input=json.dumps(spec), capture_output=True, text=True, encoding="utf-8",
                       timeout=600)
    rows = [json.loads(x) for x in r.stdout.splitlines() if x.startswith("{")]
    fatal = next((x["fatal"] for x in rows if x.get("fatal")), None)
    if fatal:
        raise RuntimeError(fatal)
    reports = [x["probe"] for x in rows if x.get("probe")]
    cmaps = probe.cmaps_for(project / "assets")
    strings, issues = probe.problems(reports, cmaps)
    accent_never_text = "text" in ((b.get("design") or {}).get("accent") or {}).get("never", [])
    for rep in reports if accent_never_text else []:  # only a pack that says so (brand.json design.accent)
        for it in accent_text(rep, b["colors"]["accent"]):
            strings.append(f"probe accent: {rep['scene']} at {rep['frame'] / 30:.2f}s: {it['detail']}")
    done = next((x for x in rows if x.get("done")), {})
    return {"frames": len(reports), "texts": sum(len(x["texts"]) for x in reports), "problems": strings,
            "blocked": done.get("blocked", []),
            "fonts": reports[0]["fonts"] if reports else {},
            "regions": sorted({t["region"] for x in reports for t in x["texts"]})}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--shots", help="also save the page at each probed time (PNG)")
    a = ap.parse_args()
    print(json.dumps(run(a.project, a.shots), ensure_ascii=False, indent=1))
