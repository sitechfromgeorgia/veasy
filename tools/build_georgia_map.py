"""Build assets/maps/georgia.json: Georgia's outline, its 12 regions and a gazetteer, projected once.

    python tools/build_georgia_map.py                    # downloads the boundaries into a fresh temp dir
    python tools/build_georgia_map.py --cache DIR        # keeps (and reuses) the downloads in DIR
    python tools/build_georgia_map.py --check-wikidata   # also compares the gazetteer with Wikidata's coordinates

Sources (licences and credit: assets/maps/README.md):
- Regions: OCHA COD-AB Georgia (data.humdata.org/dataset/cod-ab-geo), from the National Statistics Office of
  Georgia (Geostat), CC BY-IGO 3.0. It has today's lines (Tbilisi's 502 km²) and Georgia's de jure units.
- One cut line: geoBoundaries GEO ADM2 (2007, public domain), the western border of Akhalgori municipality.
- Rivers: Natural Earth 10m river centerlines and its Europe supplement (public domain): Mtkvari, Rioni, Alazani,
  Iori, Khrami, Chorokhi, Tergi; drawn clipped to Georgia's outline.
- Places: assets/maps/georgia-places.csv, a hand-checked list; coordinates from Wikidata (CC0), its QIDs kept.

Abkhazia and the Tskhinvali region are part of Georgia (Georgian law). Geostat draws the former South Ossetian
autonomous oblast as a 13th unit ("Provisional Administration"); the video draws no such entity: its Akhalgori
part (de jure Mtskheta-Mtianeti) is cut off along geoBoundaries' Akhalgori line and the rest joins Shida Kartli,
so the map has the 12 regions of Georgian law and no border Georgia doesn't draw.

How: the faces' shared borders are cut into arcs once (topology), so neighbours stay glued after simplifying;
arcs inside one region are dropped (dissolve); each arc is projected (equirectangular at Georgia's middle latitude
onto a 10000-unit-wide viewBox) and simplified (Douglas-Peucker), then written as integer SVG path data.
Pure standard library: no GIS packages needed.
"""
import argparse
import csv
import io
import json
import math
import pathlib
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "maps" / "georgia.json"
PLACES = ROOT / "assets" / "maps" / "georgia-places.csv"
COD_URL = ("https://data.humdata.org/dataset/3ee95199-2dfe-40fc-b9bd-b44cc8c91024/resource/"
           "e5f2125c-d2aa-49ee-a7d1-1fa27fb030df/download/geo_admin_boundaries.geojson.zip")
ADM2_URL = ("https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/GEO/ADM2/"
            "geoBoundaries-GEO-ADM2.geojson")
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
RIVER_FILES = ("ne_10m_rivers_lake_centerlines.geojson", "ne_10m_rivers_europe.geojson")  # public domain
AGENT = "veasy-map-build/1.0 (https://github.com/sitechfromgeorgia/veasy)"

# The projection: fixed numbers, so a point projected later lands where the build put it.
LON0, LON1, LAT0, LAT1 = 39.95, 46.80, 41.00, 43.65  # a little wider than Georgia (40.0-46.74 E, 41.05-43.59 N)
COS = math.cos(math.radians((LAT0 + LAT1) / 2))
WIDTH = 10000
K = WIDTH / ((LON1 - LON0) * COS)  # units per degree of latitude
HEIGHT = round((LAT1 - LAT0) * K)
TOLERANCE = 2.2  # Douglas-Peucker, in viewBox units (1 unit is about 57 m)

# Geostat pcode -> (id, Georgian name, English name, kind, other names a text may use)
REGIONS = {
    "GE11": ("tbilisi", "თბილისი", "Tbilisi", "capital", []),
    "GE12": ("abkhazia", "აფხაზეთი", "Abkhazia AR", "autonomous republic", ["აფხაზეთის ავტონომიური რესპუბლიკა"]),
    "GE15": ("adjara", "აჭარა", "Adjara AR", "autonomous republic", ["აჭარის ავტონომიური რესპუბლიკა"]),
    "GE23": ("guria", "გურია", "Guria", "region", []),
    "GE26": ("imereti", "იმერეთი", "Imereti", "region", []),
    "GE29": ("kakheti", "კახეთი", "Kakheti", "region", []),
    "GE32": ("mtskheta-mtianeti", "მცხეთა-მთიანეთი", "Mtskheta-Mtianeti", "region", []),
    "GE35": ("racha-lechkhumi", "რაჭა-ლეჩხუმი და ქვემო სვანეთი", "Racha-Lechkhumi and Kvemo Svaneti", "region",
             ["რაჭა-ლეჩხუმი", "რაჭა", "ლეჩხუმი", "ქვემო სვანეთი"]),
    "GE38": ("samegrelo-zemo-svaneti", "სამეგრელო-ზემო სვანეთი", "Samegrelo-Zemo Svaneti", "region",
             ["სამეგრელო", "ზემო სვანეთი", "სვანეთი"]),
    "GE41": ("samtskhe-javakheti", "სამცხე-ჯავახეთი", "Samtskhe-Javakheti", "region", ["სამცხე", "ჯავახეთი"]),
    "GE44": ("kvemo-kartli", "ქვემო ქართლი", "Kvemo Kartli", "region", []),
    "GE47": ("shida-kartli", "შიდა ქართლი", "Shida Kartli", "region", []),
}
PROVISIONAL = "GE48"  # Geostat's unit for the former South Ossetian AO: split into its regions below
AKHALGORI = (44.4831, 42.1244)  # the town, to tell the Akhalgori part from the rest
KINDS = ("city", "town", "village", "district")


def fetch(url, cache, name):
    """A download, kept in `cache` (a fresh temp dir by default: downloaded data never sits next to code)."""
    path = cache / name
    if not path.exists():
        print(f"downloading {url}", file=sys.stderr)
        req = urllib.request.Request(url, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=300) as r:
            path.write_bytes(r.read())
    return path


def geojson_from_zip(path, member):
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read(member))


def rings_of(geometry):
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return [p[0] for p in polys]  # outer rings; Georgia's units have no holes worth drawing


def key(p):
    return (round(p[0], 7), round(p[1], 7))


def inside(pt, ring):
    x, y = pt
    c, j = False, len(ring) - 1
    for i in range(len(ring)):
        (xi, yi), (xj, yj) = ring[i], ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


# ---------------------------------------------------------------- the 13th unit, split by Georgian law


def split_provisional(ring, adm2):
    """Geostat's provisional unit -> (Akhalgori part, the rest), cut along geoBoundaries' Akhalgori/Java/Gori border."""
    by_name = {f["properties"]["shapeName"]: rings_of(f["geometry"])[0] for f in adm2["features"]}
    akh = [key(p) for p in by_name["Akhalgori"][:-1]]
    west = {key(p) for n in ("Java", "Gori") for p in by_name[n]}
    flags = [p in west and inside(p, ring) for p in akh]
    best, run = [], []  # the longest run of the Akhalgori ring that is its western border and inside the unit
    for i in range(2 * len(akh)):
        if flags[i % len(akh)]:
            run.append(akh[i % len(akh)])
            if len(run) > len(best):
                best = list(run)
        else:
            run = []
    if len(best) < 10:
        raise SystemExit("the Akhalgori cut line was not found inside the provisional unit")
    pts = [key(p) for p in ring[:-1]]
    near = lambda q: min(range(len(pts)), key=lambda i: (pts[i][0] - q[0]) ** 2 + (pts[i][1] - q[1]) ** 2)  # noqa: E731
    i, j = near(best[0]), near(best[-1])
    a = (pts[i:j + 1] if i <= j else pts[i:] + pts[:j + 1]) + best[-2:0:-1]
    b = (pts[j:i + 1] if j <= i else pts[j:] + pts[:i + 1]) + best[1:-1]
    a, b = a + a[:1], b + b[:1]
    return (a, b) if inside(AKHALGORI, a) else (b, a)


# ---------------------------------------------------------------- topology


def arcs_of(faces):
    """faces [(region, ring)] -> (arcs [[points]], uses {face index: [(arc, forward)]}).
    A ring is cut wherever the faces on the other side change, so a shared border becomes one arc for both."""
    rings = []
    for _, ring in faces:
        pts = [key(p) for p in ring]
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        rings.append([p for i, p in enumerate(pts) if p != pts[i - 1]])
    owners, members = {}, {}
    for f, pts in enumerate(rings):
        for i, p in enumerate(pts):
            q = pts[(i + 1) % len(pts)]
            owners.setdefault(frozenset((p, q)), set()).add(f)
            members.setdefault(p, set()).add(f)
    arcs, index, uses = [], {}, {}
    for f, pts in enumerate(rings):
        n = len(pts)
        edge = lambda i: owners[frozenset((pts[i % n], pts[(i + 1) % n]))]  # noqa: E731
        cuts = [i for i in range(n) if edge(i - 1) != edge(i) or len(members[pts[i]]) > 2]
        if not cuts:  # a ring no other face touches: one closed arc, started at its smallest point
            s = pts.index(min(pts))
            pieces = [pts[s:] + pts[:s] + [pts[s]]]
        else:
            pieces = [[pts[k % n] for k in range(a, (b if b > a else b + n) + 1)]
                      for a, b in zip(cuts, cuts[1:] + cuts[:1])]
        for piece in pieces:
            fwd, back = tuple(piece), tuple(reversed(piece))
            canon = min(fwd, back)
            if canon not in index:
                index[canon] = len(arcs)
                arcs.append(list(canon))
            uses.setdefault(f, []).append((index[canon], fwd == canon))
    return arcs, uses


def chain(pieces):
    """Oriented point lists that join end to start -> closed rings."""
    starts = {}
    for k, p in enumerate(pieces):
        starts.setdefault(p[0], []).append(k)
    done, rings = set(), []
    for k in range(len(pieces)):
        if k in done:
            continue
        ring, cur = [], k
        while cur is not None and cur not in done:
            done.add(cur)
            ring += pieces[cur] if not ring else pieces[cur][1:]
            nxt = [c for c in starts.get(pieces[cur][-1], []) if c not in done]
            cur = nxt[0] if nxt else None
        rings.append(ring)
    return rings


# ---------------------------------------------------------------- projection, simplification, paths


def project(lon, lat):
    return ((lon - LON0) * COS * K, (LAT1 - lat) * K)


def simplify(pts, tol):
    """Douglas-Peucker with fixed endpoints (iterative)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        far, at = 0.0, None
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm if norm else math.hypot(px - ax, py - ay)
            if d > far:
                far, at = d, i
        if at is not None and far > tol:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(pts, keep) if k]


def shape(arc, tol):
    """An arc in viewBox units, simplified and rounded; a closed arc keeps at least a triangle."""
    pts = [project(*p) for p in arc]
    if pts[0] == pts[-1] and len(pts) > 4:
        h = len(pts) // 2
        out = simplify(pts[:h + 1], tol)[:-1] + simplify(pts[h:], tol)
    else:
        out = simplify(pts, tol)
    out = [(round(x), round(y)) for x, y in out]
    return [p for i, p in enumerate(out) if i == 0 or p != out[i - 1]]


def path(rings, close=True):
    """Integer points -> compact SVG path data: M x y then relative l moves, z when closed."""
    out = []
    for ring in rings:
        if close and len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]
        (x, y), moves = ring[0], []
        for nx, ny in ring[1:]:
            moves.append(f"{nx - x} {ny - y}")
            x, y = nx, ny
        out.append(f"M{ring[0][0]} {ring[0][1]}" + ("l" + " ".join(moves) if moves else "") + ("z" if close else ""))
    return "".join(out).replace(" -", "-")


def bbox(rings):
    xs = [x for r in rings for x, _ in r]
    ys = [y for r in rings for _, y in r]
    return [min(xs), min(ys), max(xs), max(ys)]


def rivers(sources, faces, tol):
    """River centerlines that run through Georgia, cut to the viewBox (the scene clips them to the outline)."""
    boxes = [(min(x for x, _ in r), min(y for _, y in r), max(x for x, _ in r), max(y for _, y in r), r) for _, r in faces]

    def in_georgia(p):
        return any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and inside(p[:2], r) for x0, y0, x1, y1, r in boxes)

    out = []
    for src in sources:
        for f in src["features"]:
            g = f["geometry"]
            if not g:
                continue
            lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
            near = (p for line in lines for p in line if LON0 <= p[0] <= LON1 and LAT0 <= p[1] <= LAT1)
            if sum(1 for _, _ in zip(range(3), (p for p in near if in_georgia(p)))) < 3:
                continue
            for line in lines:
                run = []
                for p in line + [None]:
                    if p is not None and LON0 <= p[0] <= LON1 and LAT0 <= p[1] <= LAT1:
                        run.append(tuple(p[:2]))
                    elif len(run) > 1:
                        out.append(shape(run, tol))
                        run = []
                    else:
                        run = []
    return [r for r in out if len(r) > 1]


# ---------------------------------------------------------------- places


def places(faces, regions):
    """The gazetteer: each row's region must be the one its point is in (a typo in a coordinate fails here)."""
    out = []
    with PLACES.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["id"] or row["id"].startswith("#"):
                continue
            lon, lat = float(row["lon"]), float(row["lat"])
            hit = [r for r, ring in faces if inside((lon, lat), ring)]
            if hit != [row["region"]]:
                raise SystemExit(f"place {row['id']}: the CSV says {row['region']}, the point is in {hit or 'no region'}")
            if row["kind"] not in KINDS:
                raise SystemExit(f"place {row['id']}: kind {row['kind']!r} is not one of {KINDS}")
            x, y = project(lon, lat)
            p = {"id": row["id"], "name": row["ka"], "en": row["en"], "kind": row["kind"], "region": row["region"],
                 "point": [round(x), round(y)], "q": row["qid"]}
            for col in ("aliases", "stems"):
                if row.get(col):
                    p[col] = row[col].split("|")
            out.append(p)
    ids = [p["id"] for p in out]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate place ids")
    unknown = {p["region"] for p in out} - set(regions)
    if unknown:
        raise SystemExit(f"unknown regions in the gazetteer: {unknown}")
    return out


def check_wikidata():
    """Report gazetteer rows more than 1 km from their Wikidata item's coordinates (P625)."""
    rows = [r for r in csv.DictReader(PLACES.open(encoding="utf-8")) if r["qid"].startswith("Q")]
    values = " ".join(f"wd:{r['qid']}" for r in rows)
    query = f"SELECT ?item ?c WHERE {{ VALUES ?item {{ {values} }} ?item wdt:P625 ?c }}"
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        found = {}
        for b in json.load(r)["results"]["bindings"]:
            lon, lat = map(float, b["c"]["value"][6:-1].split())
            found.setdefault(b["item"]["value"].rsplit("/", 1)[1], []).append((lon, lat))
    for r in rows:
        mine = (float(r["lon"]), float(r["lat"]))
        cands = found.get(r["qid"], [])
        if not cands:
            print(f"{r['id']}: {r['qid']} has no coordinates on Wikidata", file=sys.stderr)
            continue
        km = min(math.hypot((a - mine[0]) * 111.3 * COS, (b - mine[1]) * 111.3) for a, b in cands)
        if km > 1:
            print(f"{r['id']}: {km:.1f} km from Wikidata's {r['qid']}", file=sys.stderr)


# ---------------------------------------------------------------- build


def build(cache, tol=TOLERANCE):
    cod = geojson_from_zip(fetch(COD_URL, cache, "cod-ab-geo.geojson.zip"), "geo_admin1.geojson")
    adm2 = json.loads(fetch(ADM2_URL, cache, "geoBoundaries-GEO-ADM2.geojson").read_text(encoding="utf-8"))
    faces = []
    for f in cod["features"]:
        pcode = f["properties"]["adm1_pcode"]
        ring = rings_of(f["geometry"])
        if len(ring) != 1:
            raise SystemExit(f"{pcode}: expected one polygon, got {len(ring)}")
        if pcode == PROVISIONAL:
            akhalgori, rest = split_provisional(ring[0], adm2)
            faces += [("mtskheta-mtianeti", akhalgori), ("shida-kartli", rest)]
        elif pcode in REGIONS:
            faces.append((REGIONS[pcode][0], [key(p) for p in ring[0]]))
        else:
            raise SystemExit(f"unknown unit {pcode} {f['properties']['adm1_name']}")
    if {r for r, _ in faces} != {v[0] for v in REGIONS.values()}:
        raise SystemExit("not every region has a face")

    arcs, uses = arcs_of(faces)
    sides = {}  # arc -> the regions on its sides
    for f, us in uses.items():
        for a, _ in us:
            sides.setdefault(a, []).append(faces[f][0])
    shaped = {a: shape(arcs[a], tol) for a in sides if len(sides[a]) == 1 or len(set(sides[a])) == 2}
    outline = chain([shaped[a] if fwd else shaped[a][::-1]
                     for f, us in uses.items() for a, fwd in us if len(sides[a]) == 1])
    borders = [shaped[a] for a in sorted(shaped) if len(sides[a]) == 2]
    regions = {}
    for pcode, (rid, name, en, kind, aliases) in REGIONS.items():
        pieces = [shaped[a] if fwd else shaped[a][::-1]
                  for f, us in uses.items() if faces[f][0] == rid for a, fwd in us if a in shaped]
        rings = chain(pieces)
        regions[rid] = {"name": name, "en": en, "kind": kind, "iso": "GE-" + pcode[2:], "aliases": aliases,
                        "bbox": bbox(rings), "path": path(rings)}
    data = {
        "about": "Georgia's outline, its 12 regions (Georgian law: Abkhazia and the Tskhinvali region are part of "
                 "Georgia, drawn as no separate entity) and a gazetteer, projected for the where scene. Built by "
                 "tools/build_georgia_map.py; tt_shorts/geo.py reads it.",
        "credit": "Geostat · OCHA · CC BY-IGO",
        "sources": {
            "regions": "OCHA COD-AB Georgia (data.humdata.org/dataset/cod-ab-geo), source: National Statistics "
                       "Office of Georgia, CC BY-IGO 3.0",
            "cut": "geoBoundaries GEO ADM2 2007 (public domain): the Akhalgori line splitting the provisional unit",
            "places": "assets/maps/georgia-places.csv: coordinates from Wikidata (CC0), QIDs in each place's q",
            "rivers": "Natural Earth 10m rivers and lake centerlines + its Europe supplement (public domain)",
        },
        "projection": {"kind": "equirectangular", "lon0": LON0, "lat1": LAT1, "cos": round(COS, 6), "k": round(K, 4),
                       "x": "(lon - lon0) * cos * k", "y": "(lat1 - lat) * k"},
        "viewBox": [0, 0, WIDTH, HEIGHT],
        "tolerance": tol,
        "land": path(outline),
        "borders": path(borders, close=False),
        "rivers": path(rivers([json.loads(fetch(NE + n, cache, n).read_text(encoding="utf-8")) for n in RIVER_FILES],
                              faces, tol), close=False),
        "regions": regions,
        "places": places(faces, regions),
    }
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", help="a folder for the downloads (default: a new temp dir, deleted after)")
    ap.add_argument("--tolerance", type=float, default=TOLERANCE)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check-wikidata", action="store_true", help="compare the gazetteer with Wikidata (network)")
    a = ap.parse_args()
    if a.check_wikidata:
        check_wikidata()
    if a.cache:
        cache = pathlib.Path(a.cache)
        cache.mkdir(parents=True, exist_ok=True)
        data = build(cache, a.tolerance)
    else:
        with tempfile.TemporaryDirectory() as d:
            data = build(pathlib.Path(d), a.tolerance)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    pathlib.Path(a.out).write_text(text + "\n", encoding="utf-8")
    sizes = {k: len(json.dumps(v, ensure_ascii=False)) for k, v in data.items()}
    print(json.dumps({"out": a.out, "bytes": len(text.encode()), "regions": len(data["regions"]),
                      "places": len(data["places"]), "parts": sizes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
