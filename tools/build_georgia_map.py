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
- OpenStreetMap (ODbL 1.0, through the Overpass API; georgia-detail.json and tbilisi.json): lakes and reservoirs,
  named rivers, motorway/trunk/primary roads, main railways, and Tbilisi's 10 districts, streets, metro and water.
  Queries are by box (Georgia's, Tbilisi's), not by a country polygon, so Abkhazia and the Tskhinvali region are in;
  the lines are then cut to Georgia's outline. Downloads go to CACHE/osm-overpass/<layer>.json (a new folder per
  source); the extract's timestamp and each answer's hash are written into the files.
- The occupied territories (Georgian law: Abkhazia, and the Tskhinvali region = the former South Ossetian AO): an
  overlay in georgia.json, from the Geostat geometry above; never a region.

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
import bisect
import collections
import csv
import hashlib
import io
import json
import math
import pathlib
import re
import sys
import tempfile
import time
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
            if row.get("rank"):  # the city's order by population (Geostat, 2014 census): what a country map names first
                p["rank"] = int(row["rank"])
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


# ---------------------------------------------------------------- OpenStreetMap layers (ODbL)

OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter")
OSM_BBOX = (LAT0, LON0, LAT1, LON1)  # Overpass order: south, west, north, east
TBILISI_RELATION = 1996871  # OSM's boundary of the city of Tbilisi; its admin_level 10 children are the 10 districts
TB_BBOX = (41.58, 44.55, 41.88, 45.06)  # a little wider than Tbilisi's region
KM = 111.195 / K  # one viewBox unit in km
TOL_OVERVIEW = 9.0  # Douglas-Peucker for the whole-country layers (a scene at country zoom: 1 unit = 0.1 px)
TOL_DETAIL = 1.4  # region zoom (about 0.4-1 px per unit)
TOL_CITY, ND_CITY = 0.5, 1  # Tbilisi: 2-3 px per unit, so one decimal
TOL_CITY_MINOR = 0.9  # secondary streets and streams: a rougher line is fine
TOL_DISTRICT = 0.7  # the districts' outlines (the lines the eye follows least)
CHUNK = 40  # points per piece of a line: a scene takes the pieces that touch its view
LAKE_OVERVIEW_KM2, LAKE_DETAIL_KM2, LAKE_CITY_KM2 = 4.0, 0.25, 0.02
RIVER_MAJOR_KM, RIVER_MINOR_KM = 70.0, 25.0  # a named river's length inside Georgia
STREET_CLASSES = ("trunk", "primary", "secondary")
STREAM_KM = 2.0  # a named stream inside Tbilisi's box is drawn from this length
NOT_LAKE = "river|canal|stream|stream_pool|moat|ditch|drain|riverbank|wastewater|intermittent|oxbow|fish_pass|rapids|pond|basin"
OSM_CREDIT = "© OpenStreetMap contributors"


def bbox_str(b):
    return "(" + ",".join(str(v) for v in b) + ")"


def osm_queries():
    B, T, head = bbox_str(OSM_BBOX), bbox_str(TB_BBOX), "[out:json][timeout:600];"
    water = f'["natural"="water"]["water"!~"^({NOT_LAKE})$"]'
    return {
        "lakes": head + f'(way{water}{B};relation{water}{B};way["landuse"="reservoir"]{B};relation["landuse"="reservoir"]{B};);'
                        "out geom qt;",
        "rivers": head + f'way["waterway"="river"]["name"]{B};out geom qt;',
        "roads": head + f'way["highway"~"^(motorway|trunk|primary)$"]{B};out geom qt;',
        "rail": head + f'way["railway"="rail"][!"service"]{B};out geom qt;',
        "tbilisi-districts": head + f'rel({TBILISI_RELATION});map_to_area->.t;'
                                    'rel(area.t)["boundary"="administrative"]["admin_level"="10"];out geom qt;',
        "tbilisi-streets": head + f'way["highway"~"^(trunk|primary|secondary)$"]{T};out geom qt;',
        "tbilisi-metro": head + f'(way["railway"="subway"]{T};node["railway"="station"]["station"="subway"]{T};);'
                                "out geom qt;",
        "tbilisi-water": head + f'(way["waterway"~"^(river|stream)$"]["name"]{T};way["natural"="water"]{T};'
                                f'relation["natural"="water"]{T};);out geom qt;',
        "tbilisi-rail": head + f'way["railway"="rail"][!"service"]{T};out geom qt;',
    }


def overpass(cache, name, query):
    """One Overpass download, kept in cache/osm-overpass/<name>.json (a new folder: downloaded data never sits next to
    code). Retries and falls back to the other public instances. -> (document, {"stamp", "sha256"})."""
    folder = cache / "osm-overpass"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.json"
    if not path.exists():
        last = None
        for attempt in range(8):
            print(f"downloading OSM {name} (try {attempt + 1})", file=sys.stderr)
            req = urllib.request.Request(OVERPASS[attempt % len(OVERPASS)], headers={"User-Agent": AGENT},
                                         data=urllib.parse.urlencode({"data": query}).encode())
            try:
                with urllib.request.urlopen(req, timeout=900) as r:
                    raw = r.read()
                doc = json.loads(raw)
                if "elements" not in doc or "error" in str(doc.get("remark", "")):
                    raise ValueError(doc.get("remark") or "no elements in the answer")
                path.write_bytes(raw)
                break
            except (OSError, ValueError) as e:
                last = e
                print(f"  failed: {e}", file=sys.stderr)
                time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f"OSM {name}: no Overpass instance answered ({last})")
    raw = path.read_bytes()
    doc = json.loads(raw)
    return doc, {"stamp": doc["osm3s"]["timestamp_osm_base"], "sha256": hashlib.sha256(raw).hexdigest()[:16]}


CENTRE = (0.5137, 0.4731)  # where in a cell a Land tests the inside flag: off the middle, clear of round-number edges


class Land:
    """A region's outline on a grid: most points are tested by one lookup, only a cell the outline crosses counts
    edge crossings (clipping hundreds of thousands of OSM points against Python's point-in-polygon would crawl)."""

    def __init__(self, rings, cell=20):
        self.cell = cell
        nx, ny = WIDTH // cell + 2, HEIGHT // cell + 2
        edges = [(a, b) for r in rings for a, b in zip(r, r[1:] + r[:1])]
        self.local = {}
        for (x0, y0), (x1, y1) in edges:
            for j in range(int(min(y0, y1) // cell), int(max(y0, y1) // cell) + 1):
                for i in range(int(min(x0, x1) // cell), int(max(x0, x1) // cell) + 1):
                    self.local.setdefault((i, j), []).append(((x0, y0), (x1, y1)))
        self.flag = []
        for j in range(ny):
            yc = (j + CENTRE[1]) * cell
            xs = sorted((x1 - x0) * (yc - y0) / (y1 - y0) + x0 for (x0, y0), (x1, y1) in edges if (y0 > yc) != (y1 > yc))
            self.flag.append([bisect.bisect(xs, (i + CENTRE[0]) * cell) % 2 == 1 for i in range(nx)])

    def __contains__(self, p):
        i, j = int(p[0] // self.cell), int(p[1] // self.cell)
        if not (0 <= j < len(self.flag) and 0 <= i < len(self.flag[0])):
            return False
        inside_centre = self.flag[j][i]
        edges = self.local.get((i, j))
        if not edges:
            return inside_centre
        c = ((i + CENTRE[0]) * self.cell, (j + CENTRE[1]) * self.cell)
        hits = sum(1 for a, b in edges if crosses(c, p, a, b))
        return inside_centre != (hits % 2 == 1)


def crosses(p, q, a, b):
    """Do the segments pq and ab cross?"""
    def side(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
    d1, d2, d3, d4 = side(p, q, a), side(p, q, b), side(a, b, p), side(a, b, q)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


class Box:
    """The same `in` test for a rectangle (Tbilisi's layers are cut to the city's box)."""

    def __init__(self, box):
        self.box = box

    def __contains__(self, p):
        return self.box[0] <= p[0] <= self.box[2] and self.box[1] <= p[1] <= self.box[3]


def runs(geometry, where):
    """An OSM way's points, projected -> the runs of consecutive points that pass `where` (a Land or a Box)."""
    out, run = [], []
    for g in geometry + [None]:
        p = project(g["lon"], g["lat"]) if g else None
        if p is not None and p in where:
            run.append(p)
        else:
            if len(run) > 1:
                out.append(run)
            run = []
    return out


def merge_lines(lines):
    """Lines that meet end to end at a point no third line touches become one line (so the simplifier sees a river,
    not a hundred ways)."""
    ends = {}
    for i, l in enumerate(lines):
        for p in (l[0], l[-1]):
            ends.setdefault(p, []).append(i)
    used, out = set(), []
    for i, l in enumerate(lines):
        if i in used:
            continue
        used.add(i)
        line = list(l)
        for forward in (True, False):
            while True:
                tip = line[-1] if forward else line[0]
                nxt = [j for j in ends[tip] if j not in used]
                if len(ends[tip]) != 2 or len(nxt) != 1:
                    break
                m = lines[nxt[0]]
                used.add(nxt[0])
                if forward:
                    line += m[1:] if m[0] == tip else m[::-1][1:]
                else:
                    line = (m[:-1] if m[-1] == tip else m[::-1][:-1]) + line
        out.append(line)
    return out


def join_rings(ways):
    """Ways of points that make closed rings together (a multipolygon's outer members) -> the closed rings found;
    a ring that does not close is dropped."""
    ways = [list(w) for w in ways if len(w) > 1]
    rings = []
    while ways:
        ring = ways.pop(0)
        while ring[0] != ring[-1]:
            for k, w in enumerate(ways):
                if w[0] == ring[-1]:
                    ring += w[1:]
                elif w[-1] == ring[-1]:
                    ring += w[::-1][1:]
                elif w[-1] == ring[0]:
                    ring = w[:-1] + ring
                elif w[0] == ring[0]:
                    ring = w[::-1][:-1] + ring
                else:
                    continue
                ways.pop(k)
                break
            else:
                break
        if ring[0] == ring[-1] and len(ring) > 3:
            rings.append(ring)
    return rings


def polygon_rings(e):
    """An OSM way or multipolygon relation (from `out geom`) -> its closed outer rings as projected (x, y) lists."""
    def pts(g):
        return [project(x["lon"], x["lat"]) for x in g]
    if e["type"] == "way":
        ways = [pts(e["geometry"])] if e.get("geometry") else []
    else:
        ways = [pts(m["geometry"]) for m in e.get("members", []) if m["type"] == "way" and m.get("geometry")
                and m.get("role") in ("outer", "")]
    return join_rings(ways)


def ring_area(ring):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def fmt(v, nd):
    """A scaled integer (value x 10^nd) as the shortest decimal."""
    if not nd:
        return str(v)
    whole, frac = divmod(abs(v), 10 ** nd)
    return ("-" if v < 0 else "") + str(whole) + ("." + str(frac).rjust(nd, "0").rstrip("0") if frac else "")


def line_path(rings, close=True, nd=0):
    """path() for float points rounded to nd decimals: SVG numbers with at most nd decimals (nd 0: integers)."""
    if not nd:
        return path([[(round(x), round(y)) for x, y in r] for r in rings], close)
    q = 10 ** nd
    out = []
    for ring in rings:
        pts = [(round(x * q), round(y * q)) for x, y in ring]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        if close and len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) < 2:
            continue
        (x, y), moves = pts[0], []
        for nx, ny in pts[1:]:
            moves.append(f"{fmt(nx - x, nd)} {fmt(ny - y, nd)}")
            x, y = nx, ny
        out.append(f"M{fmt(pts[0][0], nd)} {fmt(pts[0][1], nd)}l" + " ".join(moves) + ("z" if close else ""))
    return "".join(out).replace(" -", "-")


def thin(pts, tol, nd=0):
    """Simplified and rounded; a closed ring is simplified in two halves so it stays a ring."""
    if len(pts) > 4 and pts[0] == pts[-1]:
        h = len(pts) // 2
        out = simplify(pts[:h + 1], tol)[:-1] + simplify(pts[h:], tol)
    else:
        out = simplify(pts, tol)
    out = [(round(x, nd), round(y, nd)) for x, y in out]
    return [p for i, p in enumerate(out) if i == 0 or p != out[i - 1]]


def pieces(lines, tol, nd=0):
    """Lines -> the pieces a scene picks from: [x0, y0, x1, y1, "path"], at most CHUNK points each (joined at their
    ends), the box in whole viewBox units."""
    out = []
    for line in sorted(lines, key=lambda l: (round(l[0][0]), round(l[0][1]), len(l))):
        pts = thin(line, tol, nd)
        for a in range(0, len(pts) - 1, CHUNK - 1):
            part = pts[a:a + CHUNK]
            if len(part) < 2:
                continue
            out.append([math.floor(min(x for x, _ in part)), math.floor(min(y for _, y in part)),
                        math.ceil(max(x for x, _ in part)), math.ceil(max(y for _, y in part)),
                        line_path([part], close=False, nd=nd)])
    return out


def one_path(lines, tol, nd=0):
    return line_path([p for p in (thin(l, tol, nd) for l in lines) if len(p) > 1], close=False, nd=nd)


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0 if not (dx or dy) else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def pole(ring):
    """The pole of inaccessibility of a ring (the inside point farthest from its edges) and that distance: where a
    label goes. A grid, then four rounds of finer grids around the best point."""
    edges = list(zip(ring, ring[1:] + ring[:1]))

    def depth(p):
        d = min(seg_dist(p, a, b) for a, b in edges)
        return d if inside(p, ring) else -d

    x0, y0, x1, y1 = bbox([ring])
    step = max(x1 - x0, y1 - y0) / 20
    best, bd = None, -1e9
    for i in range(21):
        for j in range(21):
            p = (x0 + i * (x1 - x0) / 20, y0 + j * (y1 - y0) / 20)
            if (d := depth(p)) > bd:
                best, bd = p, d
    for _ in range(4):
        step /= 2
        centre = best
        for i in range(-2, 3):
            for j in range(-2, 3):
                p = (centre[0] + i * step, centre[1] + j * step)
                if (d := depth(p)) > bd:
                    best, bd = p, d
    return [round(best[0]), round(best[1])], round(bd)


def lakes_from(doc, min_km2):
    """Lake and reservoir polygons of at least min_km2 -> [{"km2", "ring"}] (each one's largest outer ring,
    projected), the largest first."""
    out, seen = [], set()
    for e in doc["elements"]:
        if e["type"] not in ("way", "relation") or (e["type"], e["id"]) in seen:
            continue
        seen.add((e["type"], e["id"]))
        rings = polygon_rings(e)
        if not rings:
            continue
        ring = max(rings, key=ring_area)
        km2 = ring_area(ring) * KM * KM
        if km2 >= min_km2:
            out.append({"km2": km2, "ring": ring})
    return sorted(out, key=lambda l: (-l["km2"], l["ring"][0]))


def share_in(ring, where):
    return sum(1 for p in ring if p in where) / len(ring)


def lake_pieces(lakes, tol, nd=0):
    """Lakes -> [x0, y0, x1, y1, "path", km2], the largest first."""
    out = []
    for l in lakes:
        ring = thin(l["ring"], tol, nd)
        if len(ring) < 4:
            continue
        xs, ys = [x for x, _ in ring], [y for _, y in ring]
        out.append([math.floor(min(xs)), math.floor(min(ys)), math.ceil(max(xs)), math.ceil(max(ys)),
                    line_path([ring], nd=nd), round(l["km2"], 2)])
    return out


def line_km(line):
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(line, line[1:])) * KM


def rivers_from(doc, land):
    """Named waterway=river ways -> {"major": lines, "minor": lines}, by a river's length inside Georgia."""
    by = {}
    for e in doc["elements"]:
        t = e.get("tags", {})
        key = t.get("wikidata") or t.get("name:en") or t.get("name")
        by.setdefault(key, []).extend(runs(e["geometry"], land))
    out = {"major": [], "minor": []}
    for key, lines in sorted(by.items(), key=lambda kv: str(kv[0])):
        km = sum(line_km(l) for l in lines)
        if km >= RIVER_MAJOR_KM:
            out["major"] += merge_lines(lines)
        elif km >= RIVER_MINOR_KM:
            out["minor"] += merge_lines(lines)
    return out


def lines_by(doc, where, tag, classes):
    out = {c: [] for c in classes}
    for e in doc["elements"]:
        c = e.get("tags", {}).get(tag)
        if c in out and e["type"] == "way":
            out[c] += runs(e["geometry"], where)
    return {c: merge_lines(v) for c, v in out.items()}


def osm_layers(cache, land):
    """The country's OSM layers -> (georgia-detail.json's content, the extract notes)."""
    qs, notes = osm_queries(), {}

    def get(name):
        doc, note = overpass(cache, name, qs[name])
        notes[name] = note
        return doc

    lakes = [l for l in lakes_from(get("lakes"), LAKE_DETAIL_KM2) if share_in(l["ring"], land) >= 1 / 3]
    rivers = rivers_from(get("rivers"), land)
    roads = lines_by(get("roads"), land, "highway", ("motorway", "trunk", "primary"))
    rail = merge_lines([r for e in get("rail")["elements"] if e["type"] == "way" for r in runs(e["geometry"], land)])
    detail = {
        "overview": {
            "tolerance": TOL_OVERVIEW,
            "lakes": line_path([thin(l["ring"], TOL_OVERVIEW) for l in lakes if l["km2"] >= LAKE_OVERVIEW_KM2]),
            "rivers": one_path(rivers["major"], TOL_OVERVIEW),
            "roads": one_path(roads["motorway"] + roads["trunk"], TOL_OVERVIEW),
        },
        "tolerance": TOL_DETAIL,
        "lakes": lake_pieces(lakes, TOL_DETAIL),
        "rivers": {c: pieces(rivers[c], TOL_DETAIL) for c in ("major", "minor")},
        "roads": {c: pieces(roads[c], TOL_DETAIL) for c in ("motorway", "trunk", "primary")},
        "rail": pieces(rail, TOL_DETAIL),
    }
    return detail, notes


def tbilisi_layers(cache, box, places_list):
    """Tbilisi's layers, one decimal of a viewBox unit: the 10 districts (OSM admin_level 10, matched to the
    gazetteer), main streets, metro, water, rail. `box` is the city's box in viewBox units."""
    qs, notes, where = osm_queries(), {}, Box(box)

    def get(name):
        doc, note = overpass(cache, name, qs[name])
        notes[name] = note
        return doc

    districts = []
    by_en = {re.sub(r"[^a-z]", "", p["en"].lower().replace("gh", "g")): p for p in places_list if p["kind"] == "district"}
    for e in get("tbilisi-districts")["elements"]:
        t = e.get("tags", {})
        en = re.sub(r"[^a-z]", "", t.get("name:en", "").lower().replace(" district", "").replace("gh", "g"))
        place = by_en.get(en)
        rings = polygon_rings(e)
        if place is None or not rings:
            raise SystemExit(f"Tbilisi district {t.get('name:en') or t.get('name')} ({e['id']}): no gazetteer district "
                             "or no closed ring")
        main = max(rings, key=ring_area)
        if not inside(tuple(place["point"]), [(round(x), round(y)) for x, y in main]):
            print(f"note: {place['id']}'s gazetteer point lies outside OSM's {t.get('name:en')} polygon", file=sys.stderr)
        ring = thin(main, TOL_DISTRICT, ND_CITY)
        at, r = pole([(x, y) for x, y in ring])
        xs, ys = [x for x, _ in ring], [y for _, y in ring]
        districts.append({"id": place["id"], "name": place["name"], "osm": e["id"],
                          "bbox": [math.floor(min(xs)), math.floor(min(ys)), math.ceil(max(xs)), math.ceil(max(ys))],
                          "at": at, "r": r, "path": line_path([ring], nd=ND_CITY)})
    districts.sort(key=lambda d: d["id"])
    streets = lines_by(get("tbilisi-streets"), where, "highway", STREET_CLASSES)
    metro_doc = get("tbilisi-metro")
    metro = merge_lines([r for e in metro_doc["elements"] if e["type"] == "way" for r in runs(e["geometry"], where)])
    stations = sorted([round(x), round(y)] for x, y in (project(e["lon"], e["lat"]) for e in metro_doc["elements"]
                                                         if e["type"] == "node") if (x, y) in where)
    water_doc = get("tbilisi-water")
    waterways = {kind: [r for r in merge_lines([r for e in water_doc["elements"] if e["type"] == "way"
                                                and e.get("tags", {}).get("waterway") == kind
                                                for r in runs(e["geometry"], where)])
                        if kind == "river" or line_km(r) >= STREAM_KM] for kind in ("river", "stream")}
    lakes = [l for l in lakes_from({"elements": [e for e in water_doc["elements"] if not e.get("tags", {}).get("waterway")
                                                 and e.get("tags", {}).get("water") not in NOT_LAKE.split("|")]},
                                   LAKE_CITY_KM2) if share_in(l["ring"], where) >= 0.5]
    rail = merge_lines([r for e in get("tbilisi-rail")["elements"] if e["type"] == "way" for r in runs(e["geometry"], where)])
    return {
        "box": box, "decimals": ND_CITY, "tolerance": TOL_CITY,
        "districts": districts,
        "streets": {c: pieces(streets[c], TOL_CITY_MINOR if c == "secondary" else TOL_CITY, ND_CITY)
                    for c in STREET_CLASSES},
        "metro": pieces(metro, TOL_CITY, ND_CITY), "stations": stations,
        "rivers": pieces(waterways["river"], TOL_CITY, ND_CITY),
        "streams": pieces(waterways["stream"], TOL_CITY_MINOR, ND_CITY),
        "lakes": lake_pieces(lakes, TOL_CITY, ND_CITY),
        "rail": pieces(rail, TOL_CITY, ND_CITY),
    }, notes


# ---------------------------------------------------------------- build


def build(cache, tol=TOLERANCE):
    cod = geojson_from_zip(fetch(COD_URL, cache, "cod-ab-geo.geojson.zip"), "geo_admin1.geojson")
    adm2 = json.loads(fetch(ADM2_URL, cache, "geoBoundaries-GEO-ADM2.geojson").read_text(encoding="utf-8"))
    faces, tskhinvali = [], []  # tskhinvali: the two faces of Geostat's provisional unit
    for f in cod["features"]:
        pcode = f["properties"]["adm1_pcode"]
        ring = rings_of(f["geometry"])
        if len(ring) != 1:
            raise SystemExit(f"{pcode}: expected one polygon, got {len(ring)}")
        if pcode == PROVISIONAL:
            akhalgori, rest = split_provisional(ring[0], adm2)
            tskhinvali = [len(faces), len(faces) + 1]
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
    regions, region_rings = {}, {}
    for pcode, (rid, name, en, kind, aliases) in REGIONS.items():
        pieces = [shaped[a] if fwd else shaped[a][::-1]
                  for f, us in uses.items() if faces[f][0] == rid for a, fwd in us if a in shaped]
        rings = region_rings[rid] = chain(pieces)
        regions[rid] = {"name": name, "en": en, "kind": kind, "iso": "GE-" + pcode[2:], "aliases": aliases,
                        "bbox": bbox(rings), "path": path(rings)}
    # The territories Georgian law calls occupied (Law on Occupied Territories, 2008): the Autonomous Republic of
    # Abkhazia and the Tskhinvali region (the former South Ossetian AO). An overlay: the 12 regions stay as they are.
    # The Tskhinvali ring is cut from the same arcs as the regions, so it meets their lines exactly.
    count = collections.Counter(a for f in tskhinvali for a, _ in uses[f])
    tskh_arcs = {a: shaped[a] if a in shaped else shape(arcs[a], tol) for f in tskhinvali for a, _ in uses[f]}
    tskh = chain([tskh_arcs[a] if fwd else tskh_arcs[a][::-1]
                  for f in tskhinvali for a, fwd in uses[f] if count[a] == 1])
    occupied = {}
    for oid, name, en, rs in (("abkhazia", "აფხაზეთი", "Abkhazia", region_rings["abkhazia"]),
                              ("tskhinvali", "ცხინვალის რეგიონი", "Tskhinvali region", tskh)):
        at, r = pole(max(rs, key=ring_area))
        occupied[oid] = {"name": name, "en": en, "bbox": bbox(rs), "path": path(rs), "at": at, "r": r}
    data = {
        "about": "Georgia's outline, its 12 regions (Georgian law: Abkhazia and the Tskhinvali region are part of "
                 "Georgia, drawn as no separate entity) and a gazetteer, projected for the where scene. Built by "
                 "tools/build_georgia_map.py; tt_shorts/geo.py reads it. Its OpenStreetMap layers are in "
                 "georgia-detail.json and tbilisi.json (ODbL).",
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
        "occupied": occupied,
        "places": places(faces, regions),
    }
    return data, outline


OSM_NOTE = ("OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright), through the Overpass API "
            "(overpass-api.de): the queries are in tools/build_georgia_map.py (osm_queries), the extract's date and "
            "the downloads' hashes are in `extract`")


def build_all(cache, tol=TOLERANCE, osm=True):
    """{"georgia": ..., "georgia-detail": ..., "tbilisi": ...}: each key is a file of assets/maps/."""
    data, outline = build(cache, tol)
    if not osm:
        return {"georgia": data}
    detail, notes = osm_layers(cache, Land(outline))
    x0, y0, x1, y1 = data["regions"]["tbilisi"]["bbox"]
    pad = 0.04 * max(x1 - x0, y1 - y0)
    city, notes2 = tbilisi_layers(cache, [x0 - pad, y0 - pad, x1 + pad, y1 + pad], data["places"])
    head = {"license": "ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/ (a derived database: share-alike)",
            "credit": OSM_CREDIT, "projection": "the one in georgia.json", "sources": {"osm": OSM_NOTE}}
    data["sources"]["osm"] = "OpenStreetMap (ODbL): the layers of georgia-detail.json and tbilisi.json"
    detail = {"about": "OpenStreetMap layers of Georgia for the where scene (lakes, rivers, main roads, railways), "
                       "cut to Georgia's outline, in georgia.json's viewBox units. Built by tools/build_georgia_map.py.",
              **head, "extract": notes, **detail}
    city = {"about": "OpenStreetMap layers of Tbilisi for the where scene's district view: the 10 districts, main "
                     "streets, metro, water, rail; one decimal of a viewBox unit. Built by tools/build_georgia_map.py.",
            **head, "extract": notes2, **city}
    return {"georgia": data, "georgia-detail": detail, "tbilisi": city}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", help="a folder for the downloads (default: a new temp dir, deleted after)")
    ap.add_argument("--tolerance", type=float, default=TOLERANCE)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check-wikidata", action="store_true", help="compare the gazetteer with Wikidata (network)")
    ap.add_argument("--no-osm", action="store_true", help="only georgia.json (no OpenStreetMap layers)")
    a = ap.parse_args()
    if a.check_wikidata:
        check_wikidata()
    if a.cache:
        cache = pathlib.Path(a.cache)
        cache.mkdir(parents=True, exist_ok=True)
        files = build_all(cache, a.tolerance, not a.no_osm)
    else:
        with tempfile.TemporaryDirectory() as d:
            files = build_all(pathlib.Path(d), a.tolerance, not a.no_osm)
    out = pathlib.Path(a.out)
    report = {}
    for name, data in files.items():
        target = out if name == "georgia" else out.with_name(f"{name}.json")
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        with open(target, "w", encoding="utf-8", newline="\n") as f:  # the same bytes on any platform
            f.write(text + "\n")
        report[target.name] = {"bytes": len(text.encode()),
                               "parts": {k: len(json.dumps(v, ensure_ascii=False)) for k, v in data.items()}}
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
