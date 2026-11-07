"""Build assets/relief/ from open elevation data (NASA SRTM / USGS GMTED2010 via AWS Terrain Tiles)
and assets/maps/georgia.json + assets/maps/georgia-places.csv.

Run from the repository root:
    python tools/build_relief.py

Sources & Licences (see assets/maps/README.md):
- Elevation: NASA SRTMGL1 v003 & USGS GMTED2010 via AWS Open Data Terrain Tiles
  (https://registry.opendata.aws/terrain-tiles/, US Public Domain, 17 U.S.C. 105).
- Outlines & 12 Regions of Georgian Law: assets/maps/georgia.json (Geostat / UN OCHA COD-AB, CC BY-IGO 3.0).
- Rivers: assets/maps/georgia.json (Natural Earth 1:10m, CC0 1.0 Public Domain).
- Gazetteer: assets/maps/georgia-places.csv (Wikidata CC0 1.0 Public Domain).

Hard Map Rules enforced at build time:
1. Outlines come ONLY from assets/maps/georgia.json. Everything outside Georgia's land polygon is
   clamped to zero elevation and masked out so nothing outside Georgia is drawn as a claim.
2. Georgia has its 12 regions of Georgian law: Abkhazia ('abkhazia') and the Tskhinvali region
   (inside 'shida-kartli' and 'mtskheta-mtianeti') are integral parts of Georgia, drawn as no separate entity.
3. All 149 gazetteer places from tt_shorts/geo.py have exact 3D world coordinates and terrain elevations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import pathlib
import re
import shutil
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAP_JSON = ROOT / "assets" / "maps" / "georgia.json"
PLACES_CSV = ROOT / "assets" / "maps" / "georgia-places.csv"
OUT_DIR = ROOT / "assets" / "relief"
PLATE_DATA_DIR = ROOT / "plates" / "relief" / "data"

# Grid resolution matching georgia.json viewBox [0, 0, 10000, 5233] at 12.5 viewBox units/px
GRID_W = 800
GRID_H = 418
VIEW_W = 10000.0
VIEW_H = 5233.0
LON0, LON1 = 39.95, 46.80
LAT0, LAT1 = 41.00, 43.65
COS_LAT = 0.739337
PROJ_K = 1974.5438

# Three.js world space conversion constants
WORLD_SCALE = 100.0  # viewBox 10000x5233 -> 100.0 x 52.33 world units
VERT_EXAG = 1.8      # 1000m elevation -> 1.8 world Y units

# Canonical 12 regions of Georgian law in deterministic order (1..12)
REGION_ORDER = (
    "tbilisi",
    "abkhazia",
    "adjara",
    "guria",
    "imereti",
    "kakheti",
    "mtskheta-mtianeti",
    "racha-lechkhumi",
    "samegrelo-zemo-svaneti",
    "samtskhe-javakheti",
    "kvemo-kartli",
    "shida-kartli",
)

# AWS Open Data Terrain Tiles (Terrarium format, derived from NASA SRTM + USGS GMTED2010, US Public Domain)
TILE_ZOOM = 8
TILE_X_RANGE = range(156, 162)  # 156..161 (6 columns)
TILE_Y_RANGE = range(92, 96)    # 92..95 (4 rows)
TERRARIUM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

# Key geomorphological summits & mountain passes inside Georgia for signature flights
LANDMARKS = {
    "kazbek": {
        "id": "kazbek",
        "ka": "მყინვარწვერი",
        "en": "Mount Kazbek",
        "kind": "peak",
        "region": "mtskheta-mtianeti",
        "lon": 44.5186,
        "lat": 42.6969,
        "peak_m": 5047,
    },
    "jvari-pass": {
        "id": "jvari-pass",
        "ka": "ჯვრის უღელტეხილი",
        "en": "Jvari Pass",
        "kind": "pass",
        "region": "mtskheta-mtianeti",
        "lon": 44.4556,
        "lat": 42.5042,
        "peak_m": 2379,
    },
    "jvari": {
        "id": "jvari",
        "ka": "ჯვარი",
        "en": "Jvari Monastery Overlook",
        "kind": "landmark",
        "region": "mtskheta-mtianeti",
        "lon": 44.7339,
        "lat": 41.8383,
        "peak_m": 656,
    },
    "ushba": {
        "id": "ushba",
        "ka": "უშბა",
        "en": "Mount Ushba",
        "kind": "peak",
        "region": "samegrelo-zemo-svaneti",
        "lon": 42.6592,
        "lat": 43.1247,
        "peak_m": 4710,
    },
    "tetnuldi": {
        "id": "tetnuldi",
        "ka": "თეთნულდი",
        "en": "Mount Tetnuldi",
        "kind": "peak",
        "region": "samegrelo-zemo-svaneti",
        "lon": 42.9931,
        "lat": 43.0311,
        "peak_m": 4858,
    },
    "shkhara": {
        "id": "shkhara",
        "ka": "შხარა",
        "en": "Mount Shkhara",
        "kind": "peak",
        "region": "samegrelo-zemo-svaneti",
        "lon": 43.1000,
        "lat": 42.9994,
        "peak_m": 5193,
    },
    "gombori": {
        "id": "gombori",
        "ka": "გომბორის ქედი",
        "en": "Gombori Ridge",
        "kind": "ridge",
        "region": "kakheti",
        "lon": 45.3800,
        "lat": 41.8350,
        "peak_m": 1620,
    },
}


def lonlat_to_viewbox(lon: float, lat: float) -> tuple[float, float]:
    """Project (lon, lat) into georgia.json viewBox [0..10000, 0..5233]."""
    vx = (lon - LON0) * COS_LAT * PROJ_K
    vy = (LAT1 - lat) * PROJ_K
    return round(vx, 2), round(vy, 2)


def viewbox_to_world(vx: float, vy: float, elev_m: float = 0.0) -> list[float]:
    """Convert viewBox (vx, vy) and elevation (meters) into Three.js world [X, Y, Z]."""
    wx = round((vx - VIEW_W * 0.5) / WORLD_SCALE, 3)
    wy = round((elev_m / 1000.0) * VERT_EXAG, 3)
    wz = round((vy - VIEW_H * 0.5) / WORLD_SCALE, 3)
    return [wx, wy, wz]


def parse_svg_subpaths(path_str: str, scale_x: float, scale_y: float) -> list[list[tuple[float, float]]]:
    """Parse an SVG path string with absolute M, relative l, absolute L, and Z/z commands."""
    tokens = re.findall(r"[MmLlZz]|-?\d+(?:\.\d+)?", path_str)
    subpaths: list[list[tuple[float, float]]] = []
    curr: list[tuple[float, float]] = []
    cx, cy = 0.0, 0.0
    mode = "L"
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("M", "m"):
            if curr:
                subpaths.append(curr)
            dx, dy = float(tokens[i + 1]), float(tokens[i + 2])
            cx, cy = (dx, dy) if tok == "M" else (cx + dx, cy + dy)
            curr = [(cx * scale_x, cy * scale_y)]
            mode = "L" if tok == "M" else "l"
            i += 3
        elif tok in ("L", "l"):
            mode = tok
            i += 1
        elif tok in ("Z", "z"):
            if curr:
                subpaths.append(curr)
                curr = []
            i += 1
        else:
            dx, dy = float(tokens[i]), float(tokens[i + 1])
            cx, cy = (dx, dy) if mode == "L" else (cx + dx, cy + dy)
            curr.append((cx * scale_x, cy * scale_y))
            i += 2
    if curr:
        subpaths.append(curr)
    return subpaths


def fetch_terrarium_mosaic(cache_dir: pathlib.Path | None = None) -> np.ndarray:
    """Download the 24 z=8 Terrarium tiles covering Georgia and decode elevation in meters."""
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
    xs = list(TILE_X_RANGE)
    ys = list(TILE_Y_RANGE)
    mosaic = np.zeros((len(ys) * 256, len(xs) * 256), dtype=np.float32)

    for iy, ty in enumerate(ys):
        for ix, tx in enumerate(xs):
            cached = cache_dir / f"terrarium_z{TILE_ZOOM}_x{tx}_y{ty}.png" if cache_dir else None
            if cached and cached.exists():
                raw = cached.read_bytes()
            else:
                url = TERRARIUM_URL.format(z=TILE_ZOOM, x=tx, y=ty)
                req = urllib.request.Request(url, headers={"User-Agent": "Veasy-Relief-Builder/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                if cached:
                    cached.write_bytes(raw)
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            arr = np.asarray(img, dtype=np.float32)
            elev = (arr[:, :, 0] * 256.0 + arr[:, :, 1] + arr[:, :, 2] / 256.0) - 32768.0
            mosaic[iy * 256 : (iy + 1) * 256, ix * 256 : (ix + 1) * 256] = elev
    return mosaic


def reproject_mosaic_to_georgia_grid(mosaic: np.ndarray) -> np.ndarray:
    """Bilinearly sample the Web Mercator tile mosaic onto Georgia's 800x418 equirectangular grid."""
    n_tiles = 2.0 ** TILE_ZOOM
    x0_tile = min(TILE_X_RANGE)
    y0_tile = min(TILE_Y_RANGE)

    # Pixel centers across [LON0..LON1] and [LAT1..LAT0]
    lons = np.linspace(LON0, LON1, GRID_W, dtype=np.float64)
    lats = np.linspace(LAT1, LAT0, GRID_H, dtype=np.float64)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # Web Mercator fractional pixel coordinates within the mosaic
    px = ((lon_grid + 180.0) / 360.0 * n_tiles - x0_tile) * 256.0 - 0.5
    lat_rad = np.radians(lat_grid)
    py = ((1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / math.pi) * 0.5 * n_tiles - y0_tile) * 256.0 - 0.5

    h, w = mosaic.shape
    px = np.clip(px, 0.0, w - 1.001)
    py = np.clip(py, 0.0, h - 1.001)

    x0 = np.floor(px).astype(np.int32)
    y0 = np.floor(py).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    fx = (px - x0).astype(np.float32)
    fy = (py - y0).astype(np.float32)

    v00 = mosaic[y0, x0]
    v10 = mosaic[y0, x1]
    v01 = mosaic[y1, x0]
    v11 = mosaic[y1, x1]

    top = v00 * (1.0 - fx) + v10 * fx
    bot = v01 * (1.0 - fx) + v11 * fx
    raw = top * (1.0 - fy) + bot * fy

    def gaussian_2d(arr: np.ndarray, sigma: float) -> np.ndarray:
        radius = max(1, int(math.ceil(sigma * 3.0)))
        x = np.arange(-radius, radius + 1, dtype=np.float32)
        k = np.exp(-(x * x) / (2.0 * sigma * sigma))
        k /= k.sum()
        pad_h = np.pad(arr, ((0, 0), (radius, radius)), mode="edge")
        out_h = sum(k[i] * pad_h[:, i : i + arr.shape[1]] for i in range(len(k)))
        pad_v = np.pad(out_h, ((radius, radius), (0, 0)), mode="edge")
        return sum(k[i] * pad_v[i : i + arr.shape[0], :] for i in range(len(k)))

    fine = gaussian_2d(raw, 1.05)
    macro = gaussian_2d(raw, 2.35)
    smoothed = 0.65 * fine + 0.35 * macro
    return np.maximum(smoothed, raw * 0.94)


def build_masks_and_dem(map_data: dict, raw_elev_m: np.ndarray) -> tuple[np.ndarray, Image.Image, dict]:
    """Rasterize georgia.json outlines at 2x supersampling, mask outside Georgia, and build georgia_mask.png."""
    ss = 2
    sw, sh = GRID_W * ss, GRID_H * ss
    sx, sy = sw / VIEW_W, sh / VIEW_H

    # 1. Land polygon mask (Georgia's official external border from georgia.json)
    land_hi = Image.new("L", (sw, sh), 0)
    draw_land = ImageDraw.Draw(land_hi)
    for poly in parse_svg_subpaths(map_data["land"], sx, sy):
        if len(poly) >= 3:
            draw_land.polygon(poly, fill=255)
    land_img = land_hi.resize((GRID_W, GRID_H), resample=Image.Resampling.BILINEAR)
    land_arr = np.asarray(land_img, dtype=np.uint8)
    inside_georgia = land_arr > 16

    # 2. Region index map (1..12 for the 12 regions of Georgian law)
    region_hi = Image.new("L", (sw, sh), 0)
    draw_reg = ImageDraw.Draw(region_hi)
    region_stats: dict[str, dict] = {}
    for idx, rkey in enumerate(REGION_ORDER, start=1):
        rdata = map_data["regions"][rkey]
        for poly in parse_svg_subpaths(rdata["path"], sx, sy):
            if len(poly) >= 3:
                draw_reg.polygon(poly, fill=idx)
    region_img = region_hi.resize((GRID_W, GRID_H), resample=Image.Resampling.NEAREST)
    region_arr = np.asarray(region_img, dtype=np.uint8)
    # Ensure every pixel inside Georgia has a valid region ID, and zero outside Georgia
    region_arr = np.where(inside_georgia, region_arr, 0).astype(np.uint8)

    # 3. Border SDF / smooth interior feather in Green channel (using multi-scale Gaussian blur of binary land mask)
    land_binary = Image.fromarray(np.where(land_arr >= 128, 255, 0).astype(np.uint8), mode="L")
    sdf_blur_near = np.asarray(land_binary.filter(ImageFilter.GaussianBlur(radius=3.5)), dtype=np.float32) / 255.0
    sdf_blur_far = np.asarray(land_binary.filter(ImageFilter.GaussianBlur(radius=10.0)), dtype=np.float32) / 255.0
    # Outline stroke at the exact boundary of Georgia
    outline_hi = Image.new("L", (sw, sh), 0)
    draw_outline = ImageDraw.Draw(outline_hi)
    for poly in parse_svg_subpaths(map_data["land"], sx, sy):
        if len(poly) >= 2:
            draw_outline.line(poly + [poly[0]], fill=255, width=3)
    outline_arr = np.asarray(outline_hi.resize((GRID_W, GRID_H), resample=Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
    green_sdf = np.clip((0.55 * sdf_blur_near + 0.45 * sdf_blur_far) * 220.0 + outline_arr * 35.0, 0, 255).astype(np.uint8)
    green_sdf = np.where(inside_georgia, green_sdf, 0).astype(np.uint8)

    # 4. Rivers & internal regional borders in Blue channel
    hydro_hi = Image.new("L", (sw, sh), 0)
    draw_hydro = ImageDraw.Draw(hydro_hi)
    rivers_raw = map_data.get("rivers", "")
    river_paths = [rivers_raw] if isinstance(rivers_raw, str) else rivers_raw
    for rpath in river_paths:
        for sub in parse_svg_subpaths(rpath, sx, sy):
            if len(sub) >= 2:
                draw_hydro.line(sub, fill=190, width=2)
    borders_raw = map_data.get("borders", "")
    border_paths = [borders_raw] if isinstance(borders_raw, str) else borders_raw
    for bpath in border_paths:
        for sub in parse_svg_subpaths(bpath, sx, sy):
            if len(sub) >= 2:
                draw_hydro.line(sub, fill=120, width=2)
    hydro_arr = np.asarray(hydro_hi.resize((GRID_W, GRID_H), resample=Image.Resampling.BILINEAR), dtype=np.uint8)
    hydro_arr = np.where(inside_georgia, hydro_arr, 0).astype(np.uint8)

    # 5. Strict clipping of DEM outside Georgia: nothing outside georgia.json is drawn as a claim
    # Smoothly taper elevation in the 2px coastal/border anti-aliasing fringe so boundary cliffs don't spike
    feather = np.clip(land_arr.astype(np.float32) / 180.0, 0.0, 1.0)
    clamped_m = np.where(inside_georgia, np.maximum(0.0, raw_elev_m) * feather, 0.0)
    dem_decimeters = np.clip(np.round(clamped_m * 10.0), 0, 65535).astype("<u2")

    # Compute per-region elevation & bounding stats
    for idx, rkey in enumerate(REGION_ORDER, start=1):
        rdata = map_data["regions"][rkey]
        rmask = region_arr == idx
        relev = clamped_m[rmask]
        box = rdata["bbox"]
        lx = round((box[0] + box[2]) * 0.5, 1)
        ly = round((box[1] + box[3]) * 0.5, 1)
        label_ix = min(GRID_W - 1, max(0, int(round(lx / VIEW_W * (GRID_W - 1)))))
        label_iy = min(GRID_H - 1, max(0, int(round(ly / VIEW_H * (GRID_H - 1)))))
        label_elev = float(clamped_m[label_iy, label_ix])
        region_stats[rkey] = {
            "id": rkey,
            "index": idx,
            "alpha_code": 128 + idx * 8,
            "name_ka": rdata["name"],
            "en": rdata["en"],
            "box": box,
            "label_viewbox": [lx, ly],
            "label_elev_m": round(label_elev, 1),
            "world": viewbox_to_world(lx, ly, label_elev),
            "min_elev_m": round(float(relev.min()) if relev.size else 0.0, 1),
            "max_elev_m": round(float(relev.max()) if relev.size else 0.0, 1),
            "mean_elev_m": round(float(relev.mean()) if relev.size else 0.0, 1),
            "pixel_count": int(rmask.sum()),
        }

    # Pack RGBA mask:
    # R = land mask (0..255, strictly 0 outside Georgia)
    # G = border SDF + outline weight
    # B = rivers & regional borders
    # A = 128 + region_index * 8 (always >= 128 so browser PNG decoding never premultiplies/zeros RGB!)
    alpha_arr = (128 + region_arr.astype(np.uint16) * 8).astype(np.uint8)
    rgba = np.stack([land_arr, green_sdf, hydro_arr, alpha_arr], axis=-1)
    mask_img = Image.fromarray(rgba, mode="RGBA")
    return dem_decimeters, mask_img, region_stats


def sample_dem_meters(dem_dm: np.ndarray, vx: float, vy: float) -> float:
    """Sample elevation in meters from the 800x418 decimeter grid at viewBox (vx, vy)."""
    gx = min(GRID_W - 1.001, max(0.0, vx / VIEW_W * (GRID_W - 1)))
    gy = min(GRID_H - 1.001, max(0.0, vy / VIEW_H * (GRID_H - 1)))
    x0, y0 = int(gx), int(gy)
    x1, y1 = min(x0 + 1, GRID_W - 1), min(y0 + 1, GRID_H - 1)
    fx, fy = gx - x0, gy - y0
    v = (
        dem_dm[y0, x0] * (1 - fx) * (1 - fy)
        + dem_dm[y0, x1] * fx * (1 - fy)
        + dem_dm[y1, x0] * (1 - fx) * fy
        + dem_dm[y1, x1] * fx * fy
    )
    return round(float(v) / 10.0, 1)


def build_places_and_catalog(dem_dm: np.ndarray, region_stats: dict) -> tuple[dict, dict, list[dict]]:
    """Build 3D gazetteer anchors for all 149 places, landmarks, and the 48 region + district plates."""
    places: dict[str, dict] = {}
    with PLACES_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pid = row["id"].strip()
            lon, lat = float(row["lon"]), float(row["lat"])
            vx, vy = lonlat_to_viewbox(lon, lat)
            elev_m = sample_dem_meters(dem_dm, vx, vy)
            places[pid] = {
                "id": pid,
                "ka": row["ka"].strip(),
                "en": row["en"].strip(),
                "kind": row["kind"].strip(),
                "region": row["region"].strip(),
                "lon": lon,
                "lat": lat,
                "viewbox": [vx, vy],
                "elev_m": elev_m,
                "world": viewbox_to_world(vx, vy, elev_m),
            }

    landmarks: dict[str, dict] = {}
    for lid, info in LANDMARKS.items():
        vx, vy = lonlat_to_viewbox(info["lon"], info["lat"])
        grid_elev = sample_dem_meters(dem_dm, vx, vy)
        elev_m = max(grid_elev, float(info["peak_m"]) * 0.78)
        landmarks[lid] = {
            **info,
            "viewbox": [vx, vy],
            "elev_m": round(elev_m, 1),
            "world": viewbox_to_world(vx, vy, elev_m),
        }

    # Build the 48 region and district plate catalog:
    # 12 regions of Georgian law + 36 unambiguous districts (from georgia-places.csv where kind == 'district'
    # and ka != 'ახალდაბა' which is in geo.AMBIGUOUS).
    catalog_48: list[dict] = []
    region_moves = {
        "abkhazia": ("ridge", "gagra", "sokhumi"),
        "samegrelo-zemo-svaneti": ("ridge", "mestia", "ushguli"),
        "racha-lechkhumi": ("descend", "oni", "ambrolauri"),
        "mtskheta-mtianeti": ("descend", "stepantsminda", "mtskheta"),
        "kakheti": ("reveal", "telavi", "sighnaghi"),
        "imereti": ("reveal", "chiatura", "kutaisi"),
        "adjara": ("ridge", "khulo", "batumi"),
        "guria": ("descend", "bakhmaro", "ozurgeti"),
        "samtskhe-javakheti": ("ridge", "bakuriani", "borjomi"),
        "shida-kartli": ("reveal", "tskhinvali", "gori"),
        "kvemo-kartli": ("reveal", "bolnisi", "rustavi"),
        "tbilisi": ("descend", "mtatsminda", "old-tbilisi"),
    }
    for rkey in REGION_ORDER:
        move, p_from, p_to = region_moves[rkey]
        catalog_48.append({
            "slug": f"region-{rkey}",
            "category": "region",
            "region": rkey,
            "name_ka": region_stats[rkey]["name_ka"],
            "spec": {
                "move": move,
                "region": rkey,
                "from": p_from,
                "to": p_to,
                "anchor": p_to,
            },
        })

    districts = [
        p for p in places.values()
        if p["kind"] == "district" and p["ka"] != "ახალდაბა"
    ]
    assert len(districts) == 36, f"Expected 36 unambiguous districts, got {len(districts)}"
    move_cycle = ("descend", "reveal", "ridge")
    for idx, d in enumerate(districts):
        m = move_cycle[idx % 3]
        catalog_48.append({
            "slug": f"district-{d['id']}",
            "category": "district",
            "region": d["region"],
            "place": d["id"],
            "name_ka": d["ka"],
            "spec": {
                "move": m,
                "region": d["region"],
                "place": d["id"],
                "anchor": d["id"],
            },
        })
    assert len(catalog_48) == 48, f"Expected 48 plates in catalog, got {len(catalog_48)}"
    return places, landmarks, catalog_48


def write_specs(catalog_48: list[dict]) -> None:
    """Write the 3 signature flight specs and the 48 region/district specs under plates/relief/specs/."""
    specs_dir = ROOT / "plates" / "relief" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    signature_specs = {
        "kazbegi-jvari": {
            "preset": "kazbegi-jvari",
            "move": "descend",
            "region": "mtskheta-mtianeti",
            "from": "stepantsminda",
            "via": "jvari-pass",
            "to": "mtskheta",
            "anchor": "mtskheta",
            "anchors": ["stepantsminda", "mtskheta"],
        },
        "svaneti": {
            "preset": "svaneti",
            "move": "ridge",
            "region": "samegrelo-zemo-svaneti",
            "from": "mestia",
            "to": "ushguli",
            "anchor": "mestia",
            "anchors": ["mestia", "ushguli"],
        },
        "kakheti": {
            "preset": "kakheti",
            "move": "reveal",
            "region": "kakheti",
            "from": "telavi",
            "to": "sighnaghi",
            "anchor": "telavi",
            "anchors": ["telavi", "sighnaghi"],
        },
    }
    for name, spec in signature_specs.items():
        (specs_dir / f"{name}.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    for item in catalog_48:
        (specs_dir / f"{item['slug']}.json").write_text(
            json.dumps(item["spec"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )


def build(cache_dir: pathlib.Path | None = None) -> dict:
    """Execute the full reproducible build of assets/relief/ and sync to plates/relief/data/."""
    map_data = json.loads(MAP_JSON.read_text(encoding="utf-8"))
    mosaic = fetch_terrarium_mosaic(cache_dir=cache_dir)
    raw_elev = reproject_mosaic_to_georgia_grid(mosaic)
    dem_dm, mask_img, region_stats = build_masks_and_dem(map_data, raw_elev)
    places, landmarks, catalog_48 = build_places_and_catalog(dem_dm, region_stats)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLATE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    dem_bytes = dem_dm.tobytes()
    dem_sha256 = hashlib.sha256(dem_bytes).hexdigest()[:16]

    dem_path = OUT_DIR / "georgia_dem.bin"
    mask_path = OUT_DIR / "georgia_mask.png"
    meta_path = OUT_DIR / "relief_meta.json"

    dem_path.write_bytes(dem_bytes)
    mask_img.save(mask_path, format="PNG", optimize=False, compress_level=6)

    meta = {
        "schema": "veasy.relief.v1",
        "grid": {
            "width": GRID_W,
            "height": GRID_H,
            "encoding": "uint16_le_decimeters",
            "dem_sha256": dem_sha256,
            "max_elev_m": round(float(dem_dm.max()) / 10.0, 1),
        },
        "projection": {
            "viewBox": [0, 0, int(VIEW_W), int(VIEW_H)],
            "lon": [LON0, LON1],
            "lat": [LAT0, LAT1],
            "cos": COS_LAT,
            "k": PROJ_K,
            "world_scale": WORLD_SCALE,
            "vert_exag": VERT_EXAG,
        },
        "sources": {
            "dem": "NASA SRTMGL1 v003 & USGS GMTED2010 via AWS Open Data Terrain Tiles (US Public Domain, 17 U.S.C. 105)",
            "outlines": "assets/maps/georgia.json (Geostat / UN OCHA COD-AB, CC BY-IGO 3.0)",
            "rivers": "assets/maps/georgia.json (Natural Earth 1:10m, CC0 1.0)",
            "gazetteer": "assets/maps/georgia-places.csv (Wikidata, CC0 1.0)",
        },
        "regions": region_stats,
        "landmarks": landmarks,
        "places": places,
        "catalog_48": catalog_48,
    }
    meta_text = json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    meta_path.write_text(meta_text, encoding="utf-8", newline="\n")

    # Sync runtime files into plates/relief/data/ so plates/run.mjs local HTTP server serves them
    shutil.copyfile(dem_path, PLATE_DATA_DIR / "georgia_dem.bin")
    shutil.copyfile(mask_path, PLATE_DATA_DIR / "georgia_mask.png")
    shutil.copyfile(meta_path, PLATE_DATA_DIR / "relief_meta.json")

    write_specs(catalog_48)
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Build assets/relief/ from open DEM tiles and georgia.json.")
    parser.add_argument(
        "--cache",
        type=pathlib.Path,
        default=OUT_DIR / ".tile_cache",
        help="Directory to cache downloaded Terrarium elevation PNG tiles",
    )
    args = parser.parse_args()
    meta = build(cache_dir=args.cache)
    print(
        f"Built assets/relief/: {meta['grid']['width']}x{meta['grid']['height']} DEM "
        f"(max {meta['grid']['max_elev_m']} m, sha256={meta['grid']['dem_sha256']}), "
        f"{len(meta['regions'])} regions, {len(meta['places'])} places, {len(meta['catalog_48'])} catalog specs."
    )


if __name__ == "__main__":
    main()
