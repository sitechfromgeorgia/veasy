"""Reusable composable building blocks for the HyperFrames composed lane (docs/plan-v2.md, phase 4).

Blocks live in compose/blocks/<id>/:
  block.json     metadata, label, about, slots (kind, label, example), beats, recommended duration
  template.html  sub-composition HTML (<template>) with {id} and {slot_<name>} placeholders

Each block satisfies:
  - Facts bound never typed (data-var-text)
  - DOM text in data-probe="scene"
  - Strict safe zone (y: 248-1380, below y: 1100 no text right of x: 940)
  - Brand theme tokens only (var(--ink), var(--panel), var(--canvas), var(--accent), etc.)
  - Deterministic GSAP timeline registered on window.__timelines["{id}"]
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "compose"
BLOCKS_DIR = COMPOSE / "blocks"


class BlockError(ValueError):
    pass


def blocks_dir():
    return BLOCKS_DIR


def list_all():
    """-> {block_id: block_manifest} for all blocks in compose/blocks/."""
    out = {}
    if not BLOCKS_DIR.exists():
        return out
    for p in sorted(BLOCKS_DIR.iterdir()):
        if p.is_dir() and (p / "block.json").exists():
            try:
                manifest = json.loads((p / "block.json").read_text(encoding="utf-8"))
                out[p.name] = manifest
            except Exception:
                continue
    return out


def get(block_id):
    """Load a single block's manifest and template HTML -> (manifest, template_html)."""
    p = BLOCKS_DIR / block_id
    if not p.is_dir() or not (p / "block.json").exists():
        raise BlockError(f"unknown block {block_id!r}; known: {', '.join(sorted(list_all())) or 'none'}")
    manifest = json.loads((p / "block.json").read_text(encoding="utf-8"))
    tmpl_file = p / "template.html"
    if not tmpl_file.exists():
        raise BlockError(f"block {block_id} is missing template.html")
    template_html = tmpl_file.read_text(encoding="utf-8")
    return manifest, template_html


def render_block(block_id, comp_id, slot_map=None):
    """Render a block into composition HTML for host `comp_id`.
    Replaces `{id}` with `comp_id`, and `{slot_<name>}` with the assigned fact/slot id.
    If a slot is not in slot_map, defaults to `slot-{comp_id}-<name>`."""
    manifest, tmpl = get(block_id)
    slot_map = slot_map or {}
    text = tmpl.replace("{id}", comp_id)

    # Replace each slot placeholder
    for sname in manifest.get("slots", {}):
        placeholder = f"{{slot_{sname}}}"
        target_id = slot_map.get(sname, f"slot-{comp_id}-{sname}")
        text = text.replace(placeholder, target_id)

    # Any remaining {slot_*} placeholders
    text = re.sub(r"\{slot_([a-zA-Z0-9_-]+)\}", lambda m: slot_map.get(m.group(1), f"slot-{comp_id}-{m.group(1)}"), text)
    return text


def options():
    """Structured block catalog for `engine options` under compose.blocks."""
    all_blocks = list_all()
    return {
        "about": "reusable, checked scene blocks an agent assembles into a composed film (compose/blocks/<id>/)",
        "count": len(all_blocks),
        "blocks": {
            bid: {
                "label": b.get("label", bid),
                "about": b.get("about", ""),
                "slots": {s: d.get("kind", "words") for s, d in b.get("slots", {}).items()},
                "recommended_seconds": b.get("recommended_seconds", [3.0, 6.0])
            }
            for bid, b in all_blocks.items()
        }
    }
