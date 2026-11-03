"""Draft and validate a new brand pack from any brand book source (plan-v2 § 10).

Accepts:
  --from <url | pdf | design.md | frame.md | json>

Extracts palette, typography, metadata; drafts brands/<name>/brand.json extending _ka;
validates contrast and schema; and renders contact sheets in both themes.
"""
from __future__ import annotations

import json
import pathlib
import re
import urllib.request
from typing import Any

from tt_shorts import brand, formats, plan, store

HEX_REGEX = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")
CSS_VAR_REGEX = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);")


def _read_source(src: str) -> str:
    """Read content from URL or local file path."""
    if src.startswith("http://") or src.startswith("https://"):
        req = urllib.request.Request(
            src,
            headers={"User-Agent": "Veasy-BrandBot/1.0 (Autonomous Video Agent)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return resp.read().decode("utf-8", errors="replace")

    path = pathlib.Path(src)
    if not path.is_file():
        raise FileNotFoundError(f"brand source file not found: {src}")
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_colors(text: str) -> dict[str, str]:
    """Extract named colors and hex candidates from source text or CSS."""
    colors: dict[str, str] = {}

    # Extract CSS variables like --accent: #FF792E or --canvas: #171817
    for name, val in CSS_VAR_REGEX.findall(text):
        clean_name = name.lower().replace("-", "")
        m = HEX_REGEX.search(val)
        if m:
            hex_val = m.group(0).upper()
            if len(hex_val) == 4:
                hex_val = f"#{hex_val[1]*2}{hex_val[2]*2}{hex_val[3]*2}"
            colors[clean_name] = hex_val

    # Extract all hex codes found
    all_hexes = [h.upper() for h in HEX_REGEX.findall(text)]
    expanded = []
    for h in all_hexes:
        if len(h) == 4:
            expanded.append(f"#{h[1]*2}{h[2]*2}{h[3]*2}")
        elif len(h) == 7:
            expanded.append(h)

    if "accent" not in colors and expanded:
        # Pick the most vibrant non-black, non-white hex as accent
        for h in expanded:
            if h not in ("#000000", "#FFFFFF", "#F8FAFC", "#05080F", "#171817"):
                colors["accent"] = h
                break
        if "accent" not in colors:
            colors["accent"] = expanded[0]

    return colors


def _ensure_contrast(colors: dict[str, str]) -> dict[str, str]:
    """Ensure a palette complies with WCAG contrast floors."""
    c = dict(colors)
    # Check contrast of ink on canvas
    ink = c["ink"]
    canvas = c["canvas"]
    if brand.contrast(ink, canvas) < brand.CONTRAST["ink"]:
        c["ink"] = "#FFFFFF" if brand.mode(c) == "dark" else "#0F172A"

    # Check muted
    muted = c["muted"]
    if brand.contrast(muted, canvas) < brand.CONTRAST["muted"]:
        c["muted"] = "#A7B0BD" if brand.mode(c) == "dark" else "#64748B"

    # Check button text on accent
    on_accent = c.get("onAccent", "#FFFFFF")
    if brand.contrast(on_accent, c["accent"]) < brand.CONTRAST["onAccent"]:
        c["onAccent"] = "#000000" if brand.contrast("#000000", c["accent"]) > brand.contrast("#FFFFFF", c["accent"]) else "#FFFFFF"

    # Check markBg
    mark_bg = c.get("markBg", c["canvas"])
    mark_ink = c.get("markInk", "#FFFFFF")
    if brand.contrast(mark_ink, mark_bg) < brand.CONTRAST["mark"]:
        c["markBg"] = "#000000" if mark_ink.upper() == "#FFFFFF" else "#FFFFFF"

    # Check waiting on caption box
    c_rgba = {k: brand.rgba(v) for k, v in c.items() if brand.rgba(v)}
    canvas_rgba = c_rgba.get("canvas", (11, 15, 23, 1.0))
    box = brand.over(canvas_rgba[:3] + (brand.CAPTION_BOX,), canvas_rgba)
    if brand.contrast(c.get("waiting", "#888888"), box) < brand.CONTRAST["waiting"]:
        c["waiting"] = "rgba(248,250,252,.5)" if brand.mode(c) == "dark" else "rgba(15,23,42,.55)"

    return c


def create_brand(name: str, source: str, output_dir: pathlib.Path | None = None,
                 render_sheets: bool = True) -> dict[str, Any]:
    """Draft a new brand pack from a source and validate it."""
    clean_name = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    if not clean_name:
        raise ValueError("brand name must contain lowercase alphanumeric characters")

    target_dir = (output_dir or brand.DIR) / clean_name
    target_dir.mkdir(parents=True, exist_ok=True)
    brand_json = target_dir / "brand.json"

    raw_text = _read_source(source)
    extracted = _extract_colors(raw_text)

    accent_color = extracted.get("accent", "#3B82F6")

    # Dark Theme
    dark_colors = {
        "canvas": extracted.get("canvas", "#0B0F17"),
        "panel": extracted.get("panel", "#141B26"),
        "ink": extracted.get("ink", "#F8FAFC"),
        "muted": extracted.get("muted", "#94A3B8"),
        "accent": accent_color,
        "line": "rgba(248,250,252,.12)",
        "lineStrong": "rgba(248,250,252,.24)",
        "grid": "rgba(248,250,252,.06)",
        "ticker": "rgba(248,250,252,.6)",
        "waiting": "rgba(248,250,252,.4)",
        "markBg": extracted.get("canvas", "#0B0F17"),
        "onAccent": "#FFFFFF",
        "markInk": "#FFFFFF",
    }
    dark_colors = _ensure_contrast(dark_colors)

    # Light Theme
    light_colors = {
        "canvas": extracted.get("canvaslight", "#F8FAFC"),
        "panel": "#FFFFFF",
        "ink": "#0F172A",
        "muted": "#475569",
        "accent": accent_color,
        "line": "rgba(15,23,42,.12)",
        "lineStrong": "rgba(15,23,42,.24)",
        "grid": "rgba(15,23,42,.06)",
        "ticker": "rgba(15,23,42,.6)",
        "waiting": "rgba(15,23,42,.55)",
        "markBg": "#0F172A",
        "onAccent": "#FFFFFF",
        "markInk": "#FFFFFF",
    }
    light_colors = _ensure_contrast(light_colors)

    pack_data = {
        "name": clean_name,
        "extends": "_ka",
        "label": clean_name.replace("-", " ").title(),
        "default_theme": "dark",
        "themes": {
            "dark": {
                "label": "Dark",
                "about": f"{clean_name.title()} dark palette",
                "allowed": True,
                "colors": dark_colors,
            },
            "light": {
                "label": "Light",
                "about": f"{clean_name.title()} light paper palette",
                "allowed": True,
                "colors": light_colors,
            },
        },
        "logo": {"kind": "tmark"},
        "wordmark": {"text": clean_name, "accent": "."},
        "link": {
            "display": f"{clean_name}.ge",
            "qr": f"https://{clean_name}.ge/stories/{{id}}",
        },
        "footer": {
            "text": f"{clean_name.title()} Project",
            "strong": f"{clean_name}.ge",
        },
        "ctas": ["მოიწონე და გააზიარე", "გამოიწერე არხი"],
        "media": {
            "providers": ["openverse", "commons"],
            "official": [f"{clean_name}.ge"],
            "own": [f"{clean_name}.ge"],
        },
        "package": {
            "more": f"ვრცლად {clean_name}.ge-ზე: {{url}}",
            "link_in_bio": f"{clean_name}.ge",
            "hashtags": [f"#{clean_name.replace('-', '')}", "#news", "#georgia"],
        },
    }

    brand_json.write_text(json.dumps(pack_data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    brand.load.cache_clear()

    # Validate drafted pack
    if target_dir.parent.resolve() == brand.DIR.resolve():
        loaded = brand.load(clean_name)
    else:
        base, base_dirs = brand._raw(pack_data.get("extends", "_ka"))
        merged = brand._merge(base, pack_data)
        dirs = [target_dir] + base_dirs
        files = brand.validate(merged, dirs)
        merged["_dir"] = str(dirs[0])
        merged["_fonts"] = files["fonts"]
        merged["_pack_logo"] = files.get("logo")
        merged["themes"] = files["themes"]
        merged["default_theme"] = files["default_theme"]
        loaded = brand._apply(merged, merged["default_theme"])

    contact_sheets: dict[str, Any] = {}
    if render_sheets:
        sample_story = store.ROOT / "stories" / "24835.json"
        if sample_story.is_file():
            # Render contact sheet for dark theme
            try:
                fmt_dark = formats.get("news", theme="dark")
                sheet_dark = plan.run(str(sample_story), fmt_dark, out=store.home() / f"brand-{clean_name}-dark.plan.jpg")
                contact_sheets["dark"] = str(sheet_dark.get("sheet"))
            except Exception as e:
                contact_sheets["dark_error"] = str(e)

            # Render contact sheet for light theme
            try:
                fmt_light = formats.get("news", theme="light")
                sheet_light = plan.run(str(sample_story), fmt_light, out=store.home() / f"brand-{clean_name}-light.plan.jpg")
                contact_sheets["light"] = str(sheet_light.get("sheet"))
            except Exception as e:
                contact_sheets["light_error"] = str(e)

    return {
        "brand": clean_name,
        "path": str(brand_json.resolve()),
        "label": loaded["label"],
        "default_theme": loaded["default_theme"],
        "themes": list(loaded["themes"].keys()),
        "accent": dark_colors["accent"],
        "validation": "valid",
        "contact_sheets": contact_sheets,
        "next_steps": [
            f"Inspect contact sheets: {contact_sheets.get('dark')} and {contact_sheets.get('light')}",
            f"Add client SVG logos into brands/{clean_name}/ if available.",
            f"Test rendering with: python -m tt_shorts.engine probe stories/24835.json --brand {clean_name} --look all",
        ],
    }
