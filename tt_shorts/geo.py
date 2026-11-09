"""Real places for the `where` scene: a place name -> Georgia's map, its region and a pin (assets/maps/georgia.json).

The data (built once by tools/build_georgia_map.py): Georgia's outline, its 12 regions as Georgian law draws them
(Abkhazia and the Tskhinvali region are part of Georgia, no separate entity), the main rivers and a gazetteer of
149 cities, towns and Tbilisi districts with Georgian names, all projected to one viewBox. Remotion never loads the file: props.py
calls attach(), which puts into a where scene only what that scene draws (the outline, the region lines, the
highlighted regions, the camera's start and end, the pins).

Two more files hold OpenStreetMap's layers (ODbL): georgia-detail.json (lakes, rivers, main roads, rail for the whole
country) and tbilisi.json (the city's districts, streets, metro, water). view() ships a scene only its level's part,
clipped to the camera's window and fitted to BUDGET characters of path data (assets/maps/README.md, "What a scene
gets"); the crime family never gets a district outline or a street. The occupied territories (Abkhazia, the Tskhinvali
region) come as an `occupied` overlay with the brand pack's label (strings.occupied).

  locate("ბათუმიდან")                    -> {"region": "adjara", "point": [x, y], "name": "ბათუმი", ...}
  locate("ვაკეში")                       -> Vake, a Tbilisi district
  locate("ახალდაბა", context="ბორჯომი")  -> the Akhaldaba of Samtskhe-Javakheti, not Tbilisi's
  scene_map({"place": "ვაკე"}, "crime")  -> Tbilisi as a region, no pin (the privacy rule)

Matching is exact after the Georgian case endings are taken off (ში, ის, ზე, ით, დან, ...): a name never matches
a word that merely starts like it. A name that several places share takes the one whose region the text also
names (or another place there names); otherwise only the region they share, else nothing.
"""
import functools
import json
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "assets" / "maps" / "georgia.json"
DETAIL = ROOT / "assets" / "maps" / "georgia-detail.json"  # OpenStreetMap: lakes, rivers, main roads, rail (ODbL)
CITY = ROOT / "assets" / "maps" / "tbilisi.json"  # OpenStreetMap: Tbilisi's districts, streets, metro, water (ODbL)
BUDGET = 80_000  # characters of path data a scene's map may carry (weight())
DETAIL_PAD = 0.05  # a region's detail layers reach this far (of the window's larger side) past the camera's last view
# What a view's layers give up first when the budget is short (the first entries stay longest).
REGION_TIERS = (("lakes", None), ("rivers", "major"), ("roads", "motorway"), ("roads", "trunk"), ("rivers", "minor"),
                ("roads", "primary"), ("rail", None))
CITY_TIERS = ("rivers", "trunk", "primary", "metro", "secondary", "lakes", "streams", "rail")
COUNTRY = ("საქართველო",)  # the whole country: the outline, no zoom, no pin
PRIVATE = ("crime",)  # families whose map stops at the region and drops no pin on a district (privacy)
MAX_PINS = 3
PAD = 0.12  # the camera's margin around a region, of its larger side
CITY_WINDOW = 0.75  # a district view shows at least this much of its city's width and height
# Endings after the full name (ბათუმი-დან, ვაკე-ში, მცხეთა-ს, საბურთალო-ზე) and after the name without its last
# vowel (ბათუმ-ში, ქუთაის-ის, ვაკ-ის, მცხეთ-იდან); a syncope stem (ისნ-ის, დიღმ-ის) takes the vowel ones only.
FULL = ("", "ში", "ს", "ზე", "დან", "მდე", "თან", "სკენ", "სთვის", "სგან", "თი", "მ")
STEM = ("ში", "ს", "ის", "ზე", "ით", "იდან", "ამდე", "თან", "ისკენ", "ისთვის", "ისგან", "მა", "ად", "ისა")
SYNCOPE = ("ის", "ით", "იდან", "ისკენ", "ისთვის", "ისგან", "ად", "ისა")
PARTICLES = ("ც", "ვე")  # ბათუმშიც, ბათუმშივე


@functools.lru_cache(maxsize=1)
def data():
    return json.loads(DATA.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def detail():
    """The country's OpenStreetMap layers, or None when the file is not there (the map then has the outline only)."""
    return json.loads(DETAIL.read_text(encoding="utf-8")) if DETAIL.exists() else None


@functools.lru_cache(maxsize=1)
def city():
    """Tbilisi's OpenStreetMap layers, or None."""
    return json.loads(CITY.read_text(encoding="utf-8")) if CITY.exists() else None


def tokens(text):
    """Lower-case words (Mtavruli folds to Mkhedruli); hyphens stay inside a word (მცხეთა-მთიანეთი)."""
    return [t.strip("-") for t in re.findall(r"[\w-]+", str(text or "").lower()) if t.strip("-")]


def _last_word(token, word, stems):
    forms = {token} | {token[:-len(p)] for p in PARTICLES if token.endswith(p) and len(token) > len(p) + 2}
    for f in forms:
        if any(f == word + e for e in FULL):
            return True
        if word[-1] in "იაე" and any(f == word[:-1] + e for e in STEM):
            return True
        if any(f == s + e for s in stems for e in SYNCOPE):
            return True
    return False


def _word(token, word):
    """A word before the last one (an adjective: ახალი ათონი, ახალ ათონში, დიდი ლილოს)."""
    return token == word or (word.endswith("ი") and token == word[:-1])


@functools.lru_cache(maxsize=1)
def _index():
    """[(words, stems, "region" | "place" | "country", [refs])], one entry per distinct name."""
    d, by = data(), {}
    for rid, r in d["regions"].items():
        for name in [r["name"], *r.get("aliases", [])]:
            by.setdefault((tuple(tokens(name)), "region"), ([], []))[0].append(rid)
    for p in d["places"]:
        for name in [p["name"], *p.get("aliases", [])]:
            refs, stems = by.setdefault((tuple(tokens(name)), "place"), ([], []))
            refs.append(p)
            stems += [s for s in p.get("stems", []) if s not in stems]
    out = [(words, tuple(stems), kind, refs) for (words, kind), (refs, stems) in by.items()]
    out += [(tuple(tokens(n)), (), "country", []) for n in COUNTRY]
    return out


def matches(text):
    """Names found in the text, longest first where they overlap: [(start, end, kind, refs)] in text order."""
    toks, found = tokens(text), []
    for words, stems, kind, refs in _index():
        n = len(words)
        for i in range(len(toks) - n + 1):
            if all(_word(toks[i + k], words[k]) for k in range(n - 1)) and _last_word(toks[i + n - 1], words[-1], stems):
                found.append((i, i + n, kind, refs))
    taken, out = set(), []
    for m in sorted(found, key=lambda m: (m[0] - m[1], m[0])):
        if not taken & set(range(m[0], m[1])):
            taken |= set(range(m[0], m[1]))
            out.append(m)
    return sorted(out, key=lambda m: m[0])


def _hints(found):
    """Regions a text names: by name, or through a place only one region has."""
    out = set()
    for _, _, kind, refs in found:
        if kind == "region":
            out |= set(refs)
        elif kind == "place" and len({p["region"] for p in refs}) == 1:
            out.add(refs[0]["region"])
    return out


def parse_area(area):
    """"ge" | "ge:<region id>" | "ge:<place id>" -> ("country" | "region" | "place", id); ValueError otherwise."""
    a = str(area or "").strip().lower()
    if a == "ge":
        return "country", None
    if a.startswith("ge:"):
        ref = a[3:]
        if ref in data()["regions"]:
            return "region", ref
        if any(p["id"] == ref for p in data()["places"]):
            return "place", ref
    raise ValueError(f"unknown area {area!r}: use ge, ge:<region> ({', '.join(data()['regions'])}) or ge:<place id> "
                     "(assets/maps/georgia-places.csv)")


def area_problems(area):
    try:
        parse_area(area)
        return []
    except ValueError as e:
        return [str(e)]


def region_id(text):
    """A region id ("kakheti"), or a Georgian name, alias or place in any case (კახეთი, კახეთში, თელავი) -> the region
    it names, or None. The map-focus scene's region: the same 12 regions the map draws."""
    s = str(text or "").strip()
    if not s:
        return None
    if s.lower() in data()["regions"]:
        return s.lower()
    toks = tokens(s)
    for rid, r in data()["regions"].items():
        if any(tokens(name) == toks for name in [r["name"], *r.get("aliases", [])]):
            return rid
    loc = locate(s)
    return loc["region"] if loc and loc["region"] else None


def region_problems(region):
    """engine.shape_problems: the map-focus scene names one of Georgia's regions."""
    if region_id(region):
        return []
    return [f"region {region!r} is not one of Georgia's regions: use a Georgian name (კახეთი, იმერეთი, შიდა ქართლი) "
            f"or one of {', '.join(data()['regions'])}"]


def focus_map(scene, family=None, strings=None):
    """A map-focus scene -> (the map it draws, the region's own name), or (None, None) for an unknown region.
    The whole outline, the one region highlighted, the camera on it; never a pin (it marks no place). The same view()
    as a where scene's region: its OpenStreetMap layers and the occupied overlay with the pack's label (`strings`)."""
    rid = region_id(scene.get("region"))
    if not rid:
        return None, None
    name = data()["regions"][rid]["name"]
    loc = {"region": rid, "regions": [rid], "point": None, "name": name, "kind": "region", "places": []}
    return view(loc, family, strings), name


def _place(p):
    return {"id": p["id"], "name": p["name"], "kind": p["kind"], "region": p["region"], "point": p["point"]}


def locate(place_text, context="", area=None):
    """A place text -> {region, point, name, kind, regions, places} or None when it is not a place in Georgia.
    region: the first region (None for the whole country); point: the first place's point (None when only a region
    is known); places: every place found, in text order. `context` (the scene's sub line) only helps choose
    between places that share a name; `area` (ge, ge:<region>, ge:<place>) overrides what the text says."""
    d = data()
    found = matches(place_text)
    hints = _hints(found) | _hints(matches(context))
    places, regions, country = [], [], False
    for _, _, kind, refs in found:
        if kind == "country":
            country = True
        elif kind == "region":
            regions += refs
        else:
            pick = refs if len(refs) == 1 else [p for p in refs if p["region"] in hints]
            if len(pick) == 1:
                places.append(pick[0])
            elif len({p["region"] for p in refs}) == 1:
                regions.append(refs[0]["region"])  # same name, same region: the region is still known
    if area:
        kind, ref = parse_area(area)
        if kind == "country":
            places, regions, country = [], [], True
        elif kind == "region":
            places, regions = [p for p in places if p["region"] == ref], [ref]
        else:
            places = [next(p for p in d["places"] if p["id"] == ref)]
            regions = []
    order = []
    for r in [p["region"] for p in places] + regions:
        if r not in order:
            order.append(r)
    if not order and not country:
        return None
    first = places[0] if places else None
    return {"region": order[0] if order else None, "regions": order,
            "point": first["point"] if first else None,
            "name": first["name"] if first else d["regions"][order[0]]["name"] if order else COUNTRY[0],
            "kind": first["kind"] if first else "region" if order else "country",
            "places": [_place(p) for p in places]}


def _pad(box, k):
    x0, y0, x1, y1 = box
    m = k * max(x1 - x0, y1 - y0)
    return [x0 - m, y0 - m, x1 + m, y1 + m]


def _union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _district_window(points, city):
    """A view inside the city around its districts: at least CITY_WINDOW of the city, kept inside the city's box."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    cw, ch = city[2] - city[0], city[3] - city[1]
    w = max(CITY_WINDOW * cw, 1.6 * (max(xs) - min(xs)))
    h = max(CITY_WINDOW * ch, 1.6 * (max(ys) - min(ys)))
    cx = min(max((min(xs) + max(xs)) / 2, city[0] + w / 2), city[2] - w / 2) if w < cw else (city[0] + city[2]) / 2
    cy = min(max((min(ys) + max(ys)) / 2, city[1] + h / 2), city[3] - h / 2) if h < ch else (city[1] + city[3]) / 2
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def _hit(box, b):
    return b[0] <= box[2] and b[2] >= box[0] and b[1] <= box[3] and b[3] >= box[1]


def _join(chunks, box):
    """The pieces of a layer that touch `box`, as one path (every piece starts with an absolute M)."""
    return "".join(c[4] for c in chunks if _hit(box, c))


def weight(m):
    """The characters of path data a map carries (its budget: BUDGET): the outline, the lines, the regions, the
    occupied territories and every layer."""
    def size(v):
        if isinstance(v, str):
            return len(v)
        if isinstance(v, dict):
            return sum(size(x) for k, x in v.items() if k not in ("id", "name", "label", "box", "decimals"))
        if isinstance(v, list):
            return sum(size(x) for x in v)
        return 0
    return sum(size(m.get(k)) for k in ("land", "borders", "rivers", "regions", "occupied", "layers"))


NAMES_MAX = 14  # the city names a view ships at most; the scene draws those that fit (mapgeo.placeNames)
NAME_KINDS = ("city", "town")  # a village is too small and a district is the city view's own (its outline's name)


def _capital():
    """Tbilisi as a city: the region's Georgian name at the middle of its districts' points (the gazetteer has the
    districts, not the city)."""
    d = data()
    pts = [p["point"] for p in d["places"] if p["region"] == "tbilisi" and p["kind"] == "district"]
    if not pts:
        return None
    return {"id": "tbilisi", "name": d["regions"]["tbilisi"]["name"], "kind": "capital",
            "point": [round(sum(p[0] for p in pts) / len(pts)), round(sum(p[1] for p in pts) / len(pts))]}


def _names(level, focus, regions, pins):
    """The city and town names a view may draw, most worth showing first (the scene keeps those that fit beside the
    pins, the occupied territories' words and one another). The country view: the capital, then the cities by their
    population (the gazetteer's `rank`, Geostat's census). A region view: the capital, then the cities, then the
    towns inside the camera's last window, the bigger and the nearer the pin first. Never a village or a district (a district
    view names its districts from their outlines), never a pinned place (its name stands under the map), never the
    capital when its own region is the one highlighted."""
    if level == "district":
        return []
    cap = _capital()
    pinned = {p["id"] for p in pins}
    places = [p for p in data()["places"] if p["kind"] in NAME_KINDS and p["id"] not in pinned]
    if level == "country":
        out = ([cap] if cap else []) + sorted((p for p in places if p.get("rank")), key=lambda p: p["rank"])
        out = out[:NAMES_MAX]
    else:
        x0, y0, x1, y1 = focus
        inside = [p for p in places if x0 <= p["point"][0] <= x1 and y0 <= p["point"][1] <= y1]
        if cap and "tbilisi" not in regions and x0 <= cap["point"][0] <= x1 and y0 <= cap["point"][1] <= y1:
            inside.append(cap)
        anchor = pins[0]["point"] if pins else [(x0 + x1) / 2, (y0 + y1) / 2]
        rank = {"capital": 0, "city": 1, "town": 2}
        out = sorted(inside, key=lambda p: (rank[p["kind"]], p.get("rank", 99), math.dist(p["point"], anchor)))[:NAMES_MAX]
    return [{"name": p["name"], "point": p["point"], "kind": p["kind"]} for p in out]


def _occupied(focus, label):
    """The territories Georgian law calls occupied (Abkhazia, the Tskhinvali region), drawn as an overlay on the
    regions: both always (the camera starts on the whole country), `in_focus` when the camera's last view meets
    them. The label is the pack's word (brand strings.occupied), not the engine's."""
    return [{"id": oid, "name": o["name"], "path": o["path"], "bbox": o["bbox"], "at": o["at"], "r": o["r"],
             "label": label, "in_focus": _hit(focus, o["bbox"])} for oid, o in data()["occupied"].items()]


def _region_layers(box, room):
    """The detail layers a region view draws, clipped to `box`: whole classes, the least important dropped first
    when they would not fit in `room` characters."""
    det, out, used = detail(), {"box": [round(v) for v in box]}, 0
    for key, cls in REGION_TIERS:
        layer = det[key][cls] if cls else det[key]
        path = _join(layer, box)
        if not path or used + len(path) > room:
            continue
        used += len(path)
        if cls:
            out.setdefault(key, {})[cls] = path
        else:
            out[key] = path
    return out


def _city_layers(box, room, named):
    """Tbilisi's layers for a district view, clipped to `box` and fitted to `room` like _region_layers; the
    districts come first and always (their outlines are the city's drawing)."""
    c = city()
    districts = [{"id": x["id"], "name": x["name"], "path": x["path"], "at": x["at"], "r": x["r"],
                  "named": x["id"] in named} for x in c["districts"] if _hit(box, x["bbox"])]
    out, used = {"box": [round(v) for v in box], "decimals": c["decimals"], "districts": districts,
                 "streets": {}}, sum(len(x["path"]) for x in districts)
    for tier in CITY_TIERS:
        if tier in c["streets"]:
            path, put = _join(c["streets"][tier], box), out["streets"]
        else:
            path, put = _join(c[tier], box), out
        if not path or used + len(path) > room:
            continue
        used += len(path)
        put[tier] = path
    stations = [p for p in c["stations"] if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]]
    if "metro" in out and stations:
        out["stations"] = stations
    return out


def _layers(m, level, focus, private, named):
    """The OpenStreetMap layers of a map (None when the files are not built): `overview`, the whole country coarse,
    always; `detail`, a region view's layers clipped to its window; `city`, Tbilisi's streets, districts and metro for
    a district view (never for the crime family: the privacy rule). Rivers (m["rivers"]) become OSM's major rivers."""
    det = detail()
    if not det:
        return None
    ov = det["overview"]
    layers = {"overview": {"lakes": ov["lakes"], "roads": ov["roads"]}}
    m["rivers"] = ov["rivers"]
    room = BUDGET - weight({**m, "layers": layers})
    box = _pad(focus, DETAIL_PAD)
    tbilisi_only = m["regions"] == [data()["regions"]["tbilisi"]["path"]]
    if level == "region" and city() and tbilisi_only and not private:
        layers["city"] = _city_layers(box, room, named)
    elif level == "district" and city() and not private:
        layers["city"] = _city_layers(box, room, named)
    elif level in ("region", "district"):
        layers["detail"] = _region_layers(box, room)
    return layers


def view(loc, family=None, strings=None):
    """A located place -> what the scene draws. The privacy rule: for the crime family (crime, incidents) the
    camera stops at the region and no pin marks a district (a part of a city where people live), and no district
    outline or street is shipped. `strings` is the brand pack's strings: the occupied territories' label."""
    d = data()
    private = family in PRIVATE
    pins = [p for p in loc["places"] if not (private and p["kind"] == "district")][:MAX_PINS]
    regions = loc["regions"]
    land = _pad(_union([r["bbox"] for r in d["regions"].values()]), 0.03)
    if not regions:
        level, focus = "country", land
    elif not private and pins and all(p["kind"] == "district" for p in pins) and len(regions) == 1:
        level, focus = "district", _district_window([p["point"] for p in pins], d["regions"][regions[0]]["bbox"])
    else:
        level, focus = "region", _pad(_union([d["regions"][r]["bbox"] for r in regions]), PAD)
    m = {"viewBox": d["viewBox"], "land": d["land"], "borders": d["borders"], "rivers": d["rivers"],
         "regions": [d["regions"][r]["path"] for r in regions], "start": land,
         "focus": [round(v) for v in focus], "pins": [p["point"] for p in pins], "level": level,
         "credit": d["credit"], "occupied": _occupied(focus, str((strings or {}).get("occupied") or "")),
         "region_names": [d["regions"][r]["name"] for r in regions], "names": _names(level, focus, regions, pins)}
    layers = _layers(m, level, focus, private, {p["id"] for p in pins})
    if layers:
        m["layers"] = layers
        m["credit"] = " · ".join(c for c in (d["credit"], detail()["credit"]) if c)
    return m


def scene_map(scene, family=None, strings=None):
    """The map a where scene draws, or None (an unknown place keeps the grid scene)."""
    context = " ".join(str(scene.get(k) or "") for k in ("sub", "headline", "kicker"))
    try:
        loc = locate(scene.get("place", ""), context, scene.get("area"))
    except ValueError:
        return None  # engine check reports a bad area; a render never fails on it
    return view(loc, family, strings) if loc else None


def attach(scenes, family=None, strings=None):
    """props.py: every where scene whose place is in Georgia gets its map, and every map-focus scene the map with its
    region highlighted and the region's own Georgian name in `place` (the writer may give a slug or another case
    ending: the screen always shows the data's name); returns the scenes. `strings`: the pack's (view())."""
    for s in scenes:
        if s.get("type") == "where":
            m = scene_map(s, family, strings)
            if m:
                s["map"] = m
        elif s.get("type") == "map-focus":
            m, name = focus_map(s, family, strings)
            if m:
                s["map"] = m
                s["place"] = name
    return scenes


def areas():
    """What `engine options` shows: the area codes a where scene can name."""
    d = data()
    return {"ge": COUNTRY[0], **{f"ge:{rid}": r["name"] for rid, r in d["regions"].items()},
            "ge:<place id>": f"one of {len(d['places'])} places in assets/maps/georgia-places.csv"}
