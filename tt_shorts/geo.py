"""Real places for the `where` scene: a place name -> Georgia's map, its region and a pin (assets/maps/georgia.json).

The data (built once by tools/build_georgia_map.py): Georgia's outline, its 12 regions as Georgian law draws them
(Abkhazia and the Tskhinvali region are part of Georgia, no separate entity), the main rivers and a gazetteer of
149 cities, towns and Tbilisi districts with Georgian names, all projected to one viewBox. Remotion never loads the file: props.py
calls attach(), which puts into a where scene only what that scene draws (the outline, the region lines, the
highlighted regions, the camera's start and end, the pins).

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
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "assets" / "maps" / "georgia.json"
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


def focus_map(scene):
    """A map-focus scene -> (the map it draws, the region's own name), or (None, None) for an unknown region.
    The whole outline, the one region highlighted, the camera on it; never a pin (it marks no place)."""
    rid = region_id(scene.get("region"))
    if not rid:
        return None, None
    name = data()["regions"][rid]["name"]
    loc = {"region": rid, "regions": [rid], "point": None, "name": name, "kind": "region", "places": []}
    return view(loc), name


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


def view(loc, family=None):
    """A located place -> what the scene draws. The privacy rule: for the crime family (crime, incidents) the
    camera stops at the region and no pin marks a district (a part of a city where people live)."""
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
    return {"viewBox": d["viewBox"], "land": d["land"], "borders": d["borders"], "rivers": d["rivers"],
            "regions": [d["regions"][r]["path"] for r in regions], "start": land,
            "focus": [round(v) for v in focus], "pins": [p["point"] for p in pins], "level": level,
            "credit": d["credit"]}


def scene_map(scene, family=None):
    """The map a where scene draws, or None (an unknown place keeps the grid scene)."""
    context = " ".join(str(scene.get(k) or "") for k in ("sub", "headline", "kicker"))
    try:
        loc = locate(scene.get("place", ""), context, scene.get("area"))
    except ValueError:
        return None  # engine check reports a bad area; a render never fails on it
    return view(loc, family) if loc else None


def attach(scenes, family=None):
    """props.py: every where scene whose place is in Georgia gets its map, and every map-focus scene the map with its
    region highlighted and the region's own Georgian name in `place` (the writer may give a slug or another case
    ending: the screen always shows the data's name); returns the scenes."""
    for s in scenes:
        if s.get("type") == "where":
            m = scene_map(s, family)
            if m:
                s["map"] = m
        elif s.get("type") == "map-focus":
            m, name = focus_map(s)
            if m:
                s["map"] = m
                s["place"] = name
    return scenes


def areas():
    """What `engine options` shows: the area codes a where scene can name."""
    d = data()
    return {"ge": COUNTRY[0], **{f"ge:{rid}": r["name"] for rid, r in d["regions"].items()},
            "ge:<place id>": f"one of {len(d['places'])} places in assets/maps/georgia-places.csv"}
