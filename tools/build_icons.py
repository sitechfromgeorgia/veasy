"""Build assets/icons/lucide.json: the stroke icons Veasy's pictograms draw (sign scenes, isotype counts, the icon motif).

    python tools/build_icons.py            # fetch lucide-static from the npm registry and rewrite the asset
    python tools/build_icons.py --check    # exit 1 when the asset is missing an icon NAMES or the stem map needs

Source: Lucide (https://lucide.dev), the npm package lucide-static at VERSION, ISC licence (a few icons come from
Feather, MIT); both texts are copied to assets/icons/LICENSE. Only the icon nodes are kept: name -> [[tag, {attr:
value}], ...] on Lucide's 24 px grid, stroke-only shapes (the stroke, its width and the colors are Remotion's: the
brand pack's ink). Tags and attributes are whitelisted here, so the asset carries geometry and nothing else.

The whitelist is every icon tt_shorts/icons.py maps a Georgian stem to, plus NAMES. No weapons, no skulls, no faces:
Veasy reports, it doesn't dramatize. Names with digits are refused, so an icon name is never read as a number (N2).
"""
import argparse
import io
import json
import pathlib
import sys
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tt_shorts import icons  # noqa: E402  (the stem map names icons the asset must have)

VERSION = "1.54.0"  # published 2026-10-09
TARBALL = f"https://registry.npmjs.org/lucide-static/-/lucide-static-{VERSION}.tgz"
OUT = ROOT / "assets" / "icons"
TAGS = {"path", "circle", "rect", "line", "polyline", "polygon", "ellipse"}
ATTRS = {"d", "cx", "cy", "r", "rx", "ry", "x", "y", "width", "height", "x1", "y1", "x2", "y2", "points"}

# Icons an agent can name in English that no Georgian stem maps to yet; the stem map (tt_shorts/icons.py) adds the
# rest (energy, water, transport, health, schools, courts, police, government, money, prices, weather, buildings,
# nature, sport, culture, tech, people), so the library is exactly what the engine can use.
NAMES = ("moon power plug-zap droplets battery-charging door-open door-closed package sparkles banknote-arrow-up "
         "banknote-arrow-down signpost lock-open").split()


def wanted():
    return sorted(set(NAMES) | set(icons.mapped()))


def fetch(url=TARBALL):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def read(blob):
    """(icon nodes, licence text) from the package tarball, read in memory: nothing from it is written or run."""
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        nodes = json.load(tar.extractfile("package/icon-nodes.json"))
        licence = tar.extractfile("package/LICENSE").read().decode("utf-8")
    return nodes, licence


def clean(node_list):
    """[[tag, attrs]] with only geometry: whitelisted tags and attributes, numbers as Lucide wrote them."""
    out = []
    for tag, attrs in node_list:
        if tag not in TAGS:
            raise ValueError(f"unexpected tag {tag}")
        out.append([tag, {k: str(v) for k, v in attrs.items() if k in ATTRS}])
    return out


def build(nodes):
    names = wanted()
    missing = [n for n in names if n not in nodes]
    if missing:
        raise SystemExit(f"not in lucide-static {VERSION}: {', '.join(missing)}")
    bad = [n for n in names if any(c.isdigit() for c in n)]
    if bad:
        raise SystemExit(f"icon names with digits read as numbers (N2): {', '.join(bad)}")
    return {"source": f"lucide-static@{VERSION}", "licence": "ISC (Lucide), MIT (icons derived from Feather)",
            "grid": 24, "icons": {n: clean(nodes[n]) for n in names}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="only verify the asset covers NAMES and the stem map")
    a = ap.parse_args()
    if a.check:
        have = set(json.loads((OUT / "lucide.json").read_text(encoding="utf-8"))["icons"])
        missing = sorted(set(wanted()) - have)
        print(json.dumps({"icons": len(have), "missing": missing}))
        return 1 if missing else 0
    nodes, licence = read(fetch())
    data = build(nodes)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lucide.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (OUT / "LICENSE").write_text(licence, encoding="utf-8")
    print(json.dumps({"icons": len(data["icons"]), "file": str(OUT / "lucide.json"),
                      "bytes": (OUT / "lucide.json").stat().st_size}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
