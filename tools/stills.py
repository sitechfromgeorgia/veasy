"""Design stills: every scene of a story in its finished state, one theme per contact sheet (no voice, no video).

  python tools/stills.py stories/24725.json [--themes A,B,C] [--out out/stills]

Writes <out>/<id>-<theme>-<n>.png per scene and <out>/<id>-<theme>-sheet.jpg (all scenes side by side).
Runs the same FIT_JS as the render, so a layout QA problem shows up here first.
"""
import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from tt_shorts.render import ASSETS, FIT_JS, SEEK_JS, browser_path  # noqa: E402
from tt_shorts.templates import H, HERO_BOTTOM, W, cta_for, scene_page  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--themes", default="A,B,C")
    ap.add_argument("--out", default=str(ROOT / "out" / "stills"))
    a = ap.parse_args()
    story = json.loads(pathlib.Path(a.story).read_text(encoding="utf-8"))
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    work = ROOT / "work" / "stills"
    work.mkdir(parents=True, exist_ok=True)
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=browser_path(), args=["--no-sandbox", "--allow-file-access-from-files"])
        page = browser.new_page(viewport={"width": W, "height": H})
        for theme in a.themes.split(","):
            ctx = {"assets": ASSETS, "id": story["id"], "date": story["date"], "sources": story.get("sources", []),
                   "category": story.get("category", "society"), "theme": theme,
                   "cta": story.get("cta") or cta_for(story["id"])}
            shots = []
            for i, s in enumerate(story["scenes"]):
                src = work / f"{story['id']}-{theme}-{i}.html"
                src.write_text(scene_page(s, ctx, 4.0), encoding="utf-8")
                page.goto(f"file://{src}", wait_until="load")
                page.evaluate("document.fonts.ready.then(() => 1)")
                problems += [f"{theme} scene {i} ({s['type']}): {b}" for b in page.evaluate(FIT_JS, HERO_BOTTOM)]
                page.evaluate(SEEK_JS, 3900)
                png = out / f"{story['id']}-{theme}-{i}.png"
                page.screenshot(path=str(png))
                shots.append(png)
            sheet = out / f"{story['id']}-{theme}-sheet.jpg"
            inputs = sum((["-i", str(s)] for s in shots), [])
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex",
                            "".join(f"[{k}:v]scale=360:640[s{k}];" for k in range(len(shots))) +
                            "".join(f"[s{k}]" for k in range(len(shots))) + f"hstack=inputs={len(shots)}",
                            "-q:v", "3", str(sheet)], check=True)
            print(f"{theme}: {len(shots)} scenes -> {sheet}")
        browser.close()
    for pr in problems:
        print("QA:", pr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
