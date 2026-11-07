#!/usr/bin/env python3
"""Build and process Veasy lit surfaces library.

Converts raw material images into seamless greyscale heightmaps and tangent-space normal maps.
Maintains assets/surfaces/LEDGER.json and enforces the <=15 MB repository budget.
Mirrors ready textures to plates/surface/textures/ for the plate runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # run as a script or as a module
from tools import surface_procedural  # noqa: E402

MAX_GIT_MB = 15.0
DEFAULT_SIZE = 512
PROCEDURAL_SIZE = 384  # keeps 20 noisy normal maps inside the 15 MB budget

# Material definitions and catalog metadata
MATERIALS_CATALOG = {
    "limestone": {
        "name": "Sedimentary Limestone",
        "category": "stone",
        "description": "Fine-grained natural limestone slab with subtle porous pitting and delicate sedimentary bedding.",
        "depth": 1.2,
        "roughness": 0.75,
        "n13_label_required": True,
    },
    "worn_plaster": {
        "name": "Worn Lime Plaster",
        "category": "mineral",
        "description": "Aged historical lime stucco with delicate hairline drying fissures and soft matte powdery tooth.",
        "depth": 1.1,
        "roughness": 0.85,
        "n13_label_required": True,
    },
    "handmade_paper": {
        "name": "Handmade Rag Paper",
        "category": "paper",
        "description": "Heavyweight cotton rag paper with organic cellulose fibers, deckle pulp clumps, and micro-creases.",
        "depth": 1.1,
        "roughness": 0.90,
        "n13_label_required": True,
    },
    "raw_wood": {
        "name": "Raw Hardwood Timber",
        "category": "wood",
        "description": "Planed unvarnished hardwood slab with fine longitudinal grain lines and delicate vascular pores.",
        "depth": 1.0,
        "roughness": 0.70,
        "n13_label_required": True,
    },
    "hammered_metal": {
        "name": "Hammered Patinated Iron",
        "category": "metal",
        "description": "Wrought antique metal plate with rhythmic planishing hammer dimples and dark oxidized patina.",
        "depth": 1.4,
        "roughness": 0.45,
        "n13_label_required": True,
    },
    "woven_cloth": {
        "name": "Raw Woven Linen",
        "category": "textile",
        "description": "Coarse unbleached natural linen fabric with interlocking orthogonal warp and weft weave.",
        "depth": 1.1,
        "roughness": 0.80,
        "n13_label_required": True,
    },
    "ornament_knot": {
        "name": "Interlaced Ribbon Knot Relief",
        "category": "ornament",
        "description": "Original architectural bas-relief carving of symmetrical continuous braided strapwork ribbon.",
        "depth": 1.6,
        "roughness": 0.65,
        "n13_label_required": True,
    },
    "ornament_rosette": {
        "name": "Radial Fluted Rosette Relief",
        "category": "ornament",
        "description": "Original 12-fold symmetrical carved rosette medallion with concentric fluted petals in stone.",
        "depth": 1.5,
        "roughness": 0.65,
        "n13_label_required": True,
    },
    "ornament_meander": {
        "name": "Stepped Key Meander Relief",
        "category": "ornament",
        "description": "Original classical Greek orthogonal key meander fret carved in porous weathered limestone.",
        "depth": 1.4,
        "roughness": 0.70,
        "n13_label_required": True,
    },
    "ornament_palmette": {
        "name": "Anthemion Palmette Fan Relief",
        "category": "ornament",
        "description": "Original stylized architectural anthemion palmette fan flanked by acanthus volutes in low stone relief.",
        "depth": 1.5,
        "roughness": 0.65,
        "n13_label_required": True,
    },
}


def compute_sha256(path: Path) -> str:
    """Compute hex sha256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def to_normalized_greyscale(img: Image.Image) -> np.ndarray:
    """Convert PIL image to Rec.709 greyscale float array normalized to [0, 1] with flat illumination."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    arr = np.array(img, dtype=np.float32) / 255.0
    # Rec. 709 luminance weights
    luma = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    # Remove low-frequency illumination gradient via downsampled smooth field
    H, W = luma.shape
    low_img = Image.fromarray((luma * 255.0).astype(np.uint8), mode="L").resize((8, 8), Image.Resampling.BOX)
    low_field = np.array(low_img.resize((W, H), Image.Resampling.BICUBIC), dtype=np.float32) / 255.0
    luma = luma - low_field + float(luma.mean())
    # Percentile clipping to eliminate sensor dead/hot pixels
    p_low, p_high = np.percentile(luma, (0.5, 99.5))
    if p_high > p_low:
        luma = np.clip((luma - p_low) / (p_high - p_low), 0.0, 1.0)
    return luma


def make_seamless_tile(arr: np.ndarray, blend_width_ratio: float = 0.25) -> np.ndarray:
    """Make 2D heightfield seamlessly tileable using separable X-then-Y periodic cosine blending."""
    H, W = arr.shape
    x = np.arange(W, dtype=np.float32)
    y = np.arange(H, dtype=np.float32)
    dx = np.clip(np.abs(x - W / 2.0) / (W * 0.38), 0.0, 1.0)
    dy = np.clip(np.abs(y - H / 2.0) / (H * 0.38), 0.0, 1.0)
    wx = 0.5 * (1.0 + np.cos(np.pi * dx))
    wy = 0.5 * (1.0 + np.cos(np.pi * dy))

    # Step 1: Make horizontally seamless across all rows
    shifted_x = np.roll(arr, W // 2, axis=1)
    seamless_x = arr * wx[None, :] + shifted_x * (1.0 - wx[None, :])

    # Step 2: Make vertically seamless across all columns (preserving horizontal continuity)
    shifted_y = np.roll(seamless_x, H // 2, axis=0)
    blended = seamless_x * wy[:, None] + shifted_y * (1.0 - wy[:, None])

    b_min, b_max = blended.min(), blended.max()
    if b_max > b_min:
        blended = (blended - b_min) / (b_max - b_min)
    return blended


def compute_scharr_normals(height: np.ndarray, depth_scale: float = 1.0) -> np.ndarray:
    """Compute tangent-space normal map using Scharr derivative kernels with periodic wrap padding.

    Returns uint8 RGB array (H, W, 3) where [R, G, B] encodes [Nx, Ny, Nz] in OpenGL convention (+Y up).
    """
    H, W = height.shape
    # Periodic pad for seamless convolution
    padded = np.pad(height, pad_width=1, mode="wrap")

    # Scharr kernels (optimal rotational symmetry)
    # Kx: partial derivative with respect to X
    # Ky: partial derivative with respect to Y
    # 3x3 neighbors:
    # [TL, TC, TR]
    # [ML, MC, MR]
    # [BL, BC, BR]
    tl = padded[:-2, :-2]
    tc = padded[:-2, 1:-1]
    tr = padded[:-2, 2:]
    ml = padded[1:-1, :-2]
    mr = padded[1:-1, 2:]
    bl = padded[2:, :-2]
    bc = padded[2:, 1:-1]
    br = padded[2:, 2:]

    # Primary gradient (micro-relief)
    dx1 = (3.0 * (tr - tl) + 10.0 * (mr - ml) + 3.0 * (br - bl)) / 32.0
    dy1 = (3.0 * (bl - tl) + 10.0 * (bc - tc) + 3.0 * (br - tr)) / 32.0

    # Secondary gradient (2-pixel smoothed for meso-relief)
    padded2 = np.pad(height, pad_width=2, mode="wrap")
    tl2 = padded2[:-4, :-4]
    tr2 = padded2[:-4, 4:]
    bl2 = padded2[4:, :-4]
    br2 = padded2[4:, 4:]
    ml2 = padded2[2:-2, :-4]
    mr2 = padded2[2:-2, 4:]
    tc2 = padded2[:-4, 2:-2]
    bc2 = padded2[4:, 2:-2]
    dx2 = (3.0 * (tr2 - tl2) + 10.0 * (mr2 - ml2) + 3.0 * (br2 - bl2)) / 64.0
    dy2 = (3.0 * (bl2 - tl2) + 10.0 * (bc2 - tc2) + 3.0 * (br2 - tr2)) / 64.0

    # Multi-scale gradient combination
    dx = (dx1 + 0.5 * dx2) * depth_scale * 3.5
    dy = (dy1 + 0.5 * dy2) * depth_scale * 3.5

    # Tangent-space normal vector: (-dx, -dy, 1.0) normalized
    # In OpenGL convention, +Y is pointing upwards on screen:
    nx = -dx
    ny = dy
    nz = np.ones_like(nx)

    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= length
    ny /= length
    nz /= length

    # Map from [-1.0, 1.0] to [0, 255]
    r = np.clip(np.round((nx * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    g = np.clip(np.round((ny * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
    b = np.clip(np.round((nz * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)

    return np.stack([r, g, b], axis=-1)


def process_material(
    material_id: str,
    raw_path: Path,
    out_dir: Path,
    plates_dir: Path | None,
    size: int = DEFAULT_SIZE,
    prompt: str = "",
    model: str = "imagen-3.0",
) -> Dict[str, Any]:
    """Process a single raw material image into height and normal textures."""
    meta = MATERIALS_CATALOG.get(material_id, {
        "name": material_id.replace("_", " ").title(),
        "category": "custom",
        "description": "Surface texture",
        "depth": 1.0,
        "roughness": 0.7,
        "n13_label_required": True,
    })

    mat_dir = out_dir / material_id
    mat_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(raw_path) as src:
        # Resize/square crop
        w, h = src.size
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        cropped = src.crop((left, top, left + min_dim, top + min_dim))
        resized = cropped.resize((size, size), Image.Resampling.LANCZOS)

        # 1. Normalized greyscale height
        height_arr = to_normalized_greyscale(resized)

        # 2. Seamless tiling
        seamless_height = make_seamless_tile(height_arr)

        # 3. Tangent-space normal map
        normal_arr = compute_scharr_normals(seamless_height, depth_scale=meta.get("depth", 1.0))

    # Save height.png (optimized 8-bit greyscale)
    height_img = Image.fromarray(np.round(seamless_height * 255.0).astype(np.uint8), mode="L")
    height_path = mat_dir / "height.png"
    height_img.save(height_path, optimize=True)

    # Save normal.png (optimized RGB)
    normal_img = Image.fromarray(normal_arr, mode="RGB")
    normal_path = mat_dir / "normal.png"
    normal_img.save(normal_path, optimize=True)

    # Save material meta.json
    mat_meta = {
        "id": material_id,
        "name": meta["name"],
        "category": meta["category"],
        "description": meta["description"],
        "dimensions": [size, size],
        "depth": meta.get("depth", 1.0),
        "roughness": meta.get("roughness", 0.7),
        "height_sha256": compute_sha256(height_path),
        "normal_sha256": compute_sha256(normal_path),
        "bytes": height_path.stat().st_size + normal_path.stat().st_size,
    }
    with open(mat_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(mat_meta, f, indent=2)

    # Mirror to plates_dir if provided
    if plates_dir:
        dest_dir = plates_dir / material_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(height_path, dest_dir / "height.png")
        shutil.copy2(normal_path, dest_dir / "normal.png")
        shutil.copy2(mat_dir / "meta.json", dest_dir / "meta.json")

    # Return ledger record
    return {
        "id": material_id,
        "name": meta["name"],
        "category": meta["category"],
        "description": meta["description"],
        "prompt": prompt,
        "model": model,
        "date": date.today().isoformat(),
        "license": "ai",
        "commercial": True,
        "n13_label_required": meta.get("n13_label_required", True),
        "files": {
            "height": f"assets/surfaces/{material_id}/height.png",
            "normal": f"assets/surfaces/{material_id}/normal.png",
            "meta": f"assets/surfaces/{material_id}/meta.json",
        },
        "dimensions": [size, size],
        "depth": meta.get("depth", 1.0),
        "roughness": meta.get("roughness", 0.7),
        "bytes": height_path.stat().st_size + normal_path.stat().st_size,
        "sha256": {
            "height": compute_sha256(height_path),
            "normal": compute_sha256(normal_path),
        },
    }


def validate_record(record: Dict[str, Any]) -> None:
    """Ledger rules: a code-drawn material is `procedural` and never `ai`; an `ai` entry has no generator."""
    lic = record.get("license")
    if record.get("generator") is not None or record.get("seed") is not None:
        if lic != "procedural":
            raise ValueError(f"{record.get('id')}: a procedural material must have license 'procedural', not {lic!r}")
        if record.get("model") or record.get("prompt"):
            raise ValueError(f"{record.get('id')}: a procedural material has no model or prompt")
    if lic == "procedural" and (record.get("generator") is None or record.get("seed") is None):
        raise ValueError(f"{record.get('id')}: license 'procedural' needs a generator and a seed")
    if lic not in ("ai", "procedural"):
        raise ValueError(f"{record.get('id')}: unknown license {lic!r}")


def process_procedural(
    material_id: str,
    out_dir: Path,
    plates_dir: Path | None,
    size: int = DEFAULT_SIZE,
    seed: int | None = None,
) -> Dict[str, Any]:
    """Draw one procedural material by code and write height.png, normal.png, meta.json (+ plates mirror)."""
    spec = surface_procedural.MATERIALS[material_id]
    seed = surface_procedural.default_seed(material_id) if seed is None else int(seed)
    height = surface_procedural.generate(material_id, seed, size)  # seamless by construction
    normal_arr = compute_scharr_normals(height, depth_scale=spec["depth"])

    mat_dir = out_dir / material_id
    mat_dir.mkdir(parents=True, exist_ok=True)
    height_path = mat_dir / "height.png"
    normal_path = mat_dir / "normal.png"
    Image.fromarray(np.round(height * 255.0).astype(np.uint8), mode="L").save(height_path, optimize=True)
    Image.fromarray(normal_arr, mode="RGB").save(normal_path, optimize=True)

    generator = f"tools/surface_procedural.py:{spec['fn'].__name__}@v{surface_procedural.GENERATOR_VERSION}"
    mat_meta = {
        "id": material_id,
        "name": spec["name"],
        "category": spec["category"],
        "description": spec["description"],
        "dimensions": [size, size],
        "depth": spec["depth"],
        "roughness": spec["roughness"],
        "height_sha256": compute_sha256(height_path),
        "normal_sha256": compute_sha256(normal_path),
        "bytes": height_path.stat().st_size + normal_path.stat().st_size,
    }
    with open(mat_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(mat_meta, f, indent=2)
    if plates_dir:
        dest = plates_dir / material_id
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("height.png", "normal.png", "meta.json"):
            shutil.copy2(mat_dir / name, dest / name)

    record = {
        "id": material_id,
        "name": spec["name"],
        "category": spec["category"],
        "description": spec["description"],
        "generator": generator,
        "seed": seed,
        "date": date.today().isoformat(),
        "license": "procedural",
        "commercial": True,
        "n13_label_required": True,
        "files": {
            "height": f"assets/surfaces/{material_id}/height.png",
            "normal": f"assets/surfaces/{material_id}/normal.png",
            "meta": f"assets/surfaces/{material_id}/meta.json",
        },
        "dimensions": [size, size],
        "depth": spec["depth"],
        "roughness": spec["roughness"],
        "bytes": mat_meta["bytes"],
        "sha256": {"height": mat_meta["height_sha256"], "normal": mat_meta["normal_sha256"]},
    }
    validate_record(record)
    return record


def build_procedural(ids: List[str], out_dir: Path, plates_dir: Path | None, size: int = DEFAULT_SIZE) -> Dict[str, Any]:
    """Draw the given procedural materials (all when empty) and merge them into LEDGER.json."""
    ledger_path = out_dir / "LEDGER.json"
    ledger: Dict[str, Any] = {"schema_version": 1, "max_git_mb": MAX_GIT_MB, "materials": {}}
    if ledger_path.exists():
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)
    for mid in ids or sorted(surface_procedural.MATERIALS):
        print(f"Drawing procedural material: {mid}")
        ledger["materials"][mid] = process_procedural(mid, out_dir, plates_dir, size)
    total_mb = calculate_dir_mb(out_dir)
    ledger["updated_at"] = date.today().isoformat()
    ledger["material_count"] = len(ledger["materials"])
    ledger["total_disk_mb"] = round(total_mb, 3)
    ledger["budget_pass"] = total_mb <= MAX_GIT_MB
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    print(f"LEDGER updated: {ledger['material_count']} materials, {total_mb:.2f} MB")
    return ledger


def calculate_dir_mb(path: Path) -> float:
    """Calculate total size in megabytes of all files in directory."""
    total = 0
    if not path.exists():
        return 0.0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total / (1024.0 * 1024.0)


def build_all(
    raw_manifest: Dict[str, Dict[str, str]],
    out_dir: Path,
    plates_dir: Path | None,
    size: int = DEFAULT_SIZE,
) -> Dict[str, Any]:
    """Build all materials from manifest and update LEDGER.json."""
    ledger_path = out_dir / "LEDGER.json"
    ledger: Dict[str, Any] = {
        "schema_version": 1,
        "updated_at": date.today().isoformat(),
        "max_git_mb": MAX_GIT_MB,
        "materials": {},
    }
    if ledger_path.exists():
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except Exception:
            pass

    materials_map = ledger.get("materials", {})

    for mat_id, item in raw_manifest.items():
        raw_file = Path(item["path"])
        if not raw_file.exists():
            print(f"Warning: raw file {raw_file} for {mat_id} not found, skipping", file=sys.stderr)
            continue
        print(f"Building surface material: {mat_id} from {raw_file.name}...")
        record = process_material(
            material_id=mat_id,
            raw_path=raw_file,
            out_dir=out_dir,
            plates_dir=plates_dir,
            size=size,
            prompt=item.get("prompt", ""),
            model=item.get("model", "imagen-3.0"),
        )
        materials_map[mat_id] = record

    total_mb = calculate_dir_mb(out_dir)
    ledger["materials"] = materials_map
    ledger["material_count"] = len(materials_map)
    ledger["total_disk_mb"] = round(total_mb, 3)
    ledger["budget_pass"] = total_mb <= MAX_GIT_MB

    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)

    print(f"LEDGER updated at {ledger_path}: {len(materials_map)} materials, total {total_mb:.2f} MB (budget <= {MAX_GIT_MB} MB: {ledger['budget_pass']})")
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description="Veasy lit surfaces builder")
    parser.add_argument("--raw-file", help="Path to raw image file for single material build")
    parser.add_argument("--material", help="Material ID (e.g. limestone, worn_plaster)")
    parser.add_argument("--prompt", default="", help="Prompt used for material generation")
    parser.add_argument("--model", default="imagen-3.0", help="Model name used")
    parser.add_argument("--manifest", help="JSON manifest mapping material_id -> {path, prompt, model}")
    parser.add_argument("--out-dir", default="assets/surfaces", help="Output directory")
    parser.add_argument("--plates-dir", default="plates/surface/textures", help="Plates textures mirror directory")
    parser.add_argument("--size", type=int, default=None, help="Texture dimension (square); default 512, 384 for procedural (budget)")
    parser.add_argument("--procedural", nargs="*", metavar="ID", help="Draw procedural materials by code (all when no id given)")
    parser.add_argument("--check", action="store_true", help="Validate existing assets and budget")

    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    plates_dir = Path(args.plates_dir) if args.plates_dir else None

    if args.check:
        total_mb = calculate_dir_mb(out_dir)
        ledger_path = out_dir / "LEDGER.json"
        if not ledger_path.exists():
            print(f"FAIL: {ledger_path} does not exist", file=sys.stderr)
            return 1
        with open(ledger_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = len(data.get("materials", {}))
        try:
            for rec in data.get("materials", {}).values():
                validate_record(rec)
        except ValueError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 1
        n_proc = sum(1 for r in data.get("materials", {}).values() if r.get("license") == "procedural")
        print(f"Surfaces audit: {count} materials ({n_proc} procedural, {count - n_proc} ai), {total_mb:.2f} MB (limit {MAX_GIT_MB} MB)")
        if count < 4:
            print("FAIL: fewer than 4 materials shipped", file=sys.stderr)
            return 1
        if total_mb > MAX_GIT_MB:
            print(f"FAIL: exceeded budget ({total_mb:.2f} MB > {MAX_GIT_MB} MB)", file=sys.stderr)
            return 1
        print("OK: assets/surfaces budget and ledger pass")
        return 0

    if args.procedural is not None:
        build_procedural(args.procedural, out_dir=out_dir, plates_dir=plates_dir, size=args.size or PROCEDURAL_SIZE)
        return 0

    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        build_all(manifest, out_dir=out_dir, plates_dir=plates_dir, size=args.size or DEFAULT_SIZE)
        return 0

    if args.raw_file and args.material:
        record = process_material(
            material_id=args.material,
            raw_path=Path(args.raw_file),
            out_dir=out_dir,
            plates_dir=plates_dir,
            size=args.size or DEFAULT_SIZE,
            prompt=args.prompt,
            model=args.model,
        )
        print(f"Successfully processed {args.material}: {record['bytes']} bytes")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
