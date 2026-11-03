"""Contact sheet generator for Veasy's icons and seed drawings across all brand themes.

Renders the complete visual library (all 250 Lucide icons and all 44 seed drawings) in
every brand pack theme (sitech:dark, sitech:light, tbilisi-today:dark, tbilisi-today:light),
with interactive theme switching, Georgian stem search, and motif inspection.

CLI usage:
    python -m tt_shorts.engine contact-sheet [--out out/contact-sheet.html] [--brand all|sitech|tbilisi-today]
"""
import html
import json
import pathlib
from typing import Any, Dict, List, Optional

from tt_shorts import brand as packs
from tt_shorts import drawings, icons

ROOT = pathlib.Path(__file__).resolve().parent.parent


def get_theme_colors(brand_name: str, theme_name: str) -> Dict[str, str]:
    """Retrieve color token mapping for a specific brand theme."""
    b = packs.load(brand_name)
    theme = b.get("themes", {}).get(theme_name)
    if not theme:
        theme = b.get("themes", {}).get(b.get("theme", "dark"), {})
    colors = theme.get("colors", {})
    return {
        "CANVAS": colors.get("canvas", "#171817"),
        "PANEL": colors.get("panel", "#1F201E"),
        "INK": colors.get("ink", "#F1EDE4"),
        "MUTED": colors.get("muted", "#B6B4AC"),
        "ACCENT": colors.get("accent", "#FF792E"),
        "LINE": colors.get("line", "rgba(241,237,228,.14)"),
        "LINE_STRONG": colors.get("lineStrong", "rgba(241,237,228,.26)"),
    }


def render_icon_svg(name: str, colors: Dict[str, str], size: int = 44) -> str:
    """Generate standalone SVG markup for a library icon in given theme colors."""
    lib = icons.library()
    icon_data = lib.get(name)
    if not icon_data:
        return ""
    shapes = icon_data if isinstance(icon_data, list) else icon_data.get("shapes", [])
    ink = colors["INK"]
    body = []
    for tag, attrs in shapes:
        attr_str = " ".join(f'{k}="{html.escape(str(v))}"' for k, v in attrs.items() if k not in ("stroke", "fill"))
        stroke = attrs.get("stroke", ink)
        fill = attrs.get("fill", "none")
        if stroke not in ("none", "transparent"):
            stroke = ink
        if fill not in ("none", "transparent"):
            fill = ink
        body.append(f'  <{tag} {attr_str} stroke="{stroke}" fill="{fill}"/>')
    inner = "\n".join(body)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{ink}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" class="icon-svg">\n{inner}\n</svg>'
    )


def render_drawing_svg(drawing: Dict[str, Any], colors: Dict[str, str], max_width: int = 400) -> str:
    """Generate standalone SVG markup for a seed drawing, replacing color tokens."""
    raw_svg = drawing.get("svg", "")
    replaced = raw_svg
    # Replace tokens
    for token, val in (
        ("ACCENT", colors["ACCENT"]),
        ("INK", colors["INK"]),
        ("MUTED", colors["MUTED"]),
        ("LINE", colors["LINE"]),
        ("CANVAS", colors["CANVAS"]),
    ):
        replaced = replaced.replace(f'"{token}"', f'"{val}"')
        replaced = replaced.replace(f"'{token}'", f"'{val}'")
    height = int(max_width * 640 / 952)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 952 640" '
        f'width="{max_width}" height="{height}" class="drawing-svg">\n'
        f'<rect width="952" height="640" fill="{colors["CANVAS"]}" rx="16"/>\n'
        f'{replaced}\n</svg>'
    )


def generate_contact_sheet_html(
    out_path: Optional[pathlib.Path] = None,
    brand_filter: str = "all",
    theme_filter: str = "all",
) -> Dict[str, Any]:
    """Build the comprehensive, interactive HTML contact sheet."""
    target = pathlib.Path(out_path) if out_path else ROOT / "out" / "contact-sheet.html"
    target.parent.mkdir(parents=True, exist_ok=True)

    all_brands = ["sitech", "tbilisi-today"] if brand_filter == "all" else [brand_filter]
    themes_to_render = []
    for b_name in all_brands:
        for t_name in ["dark", "light"]:
            if theme_filter in ("all", t_name):
                themes_to_render.append((b_name, t_name))

    lib_icons = icons.library()
    all_seeds = drawings.seeds()

    # Stems mapping: icon_name -> list of Georgian stems
    stems_by_icon: Dict[str, List[str]] = {k: list(v) for k, v in icons._BY_ICON.items()}
    total_stems = sum(len(v) for v in icons._BY_ICON.values())

    # Pre-render cards for each theme
    theme_sections = []
    for b_name, t_name in themes_to_render:
        theme_id = f"{b_name}-{t_name}"
        colors = get_theme_colors(b_name, t_name)

        # Drawings section
        drawing_cards = []
        for s in all_seeds:
            svg_html = render_drawing_svg(s, colors, max_width=320)
            stems = stems_by_icon.get(s["motif"], [])
            stem_badge = f'<span class="badge stem">{html.escape(stems[0])}</span>' if stems else ""
            drawing_cards.append(f"""
            <div class="card drawing-card" data-name="{html.escape(s['name'])}" data-motif="{html.escape(s['motif'])}">
              <div class="drawing-preview">{svg_html}</div>
              <div class="card-meta">
                <div class="card-title"><strong>{html.escape(s['name'])}</strong> {stem_badge}</div>
                <div class="card-sub">motif: <code>{html.escape(s['motif'])}</code></div>
                <div class="card-about">{html.escape(s.get('about', ''))}</div>
              </div>
            </div>
            """)

        # Icons section
        icon_cards = []
        for icon_name in sorted(lib_icons.keys()):
            svg_html = render_icon_svg(icon_name, colors, size=40)
            stems = stems_by_icon.get(icon_name, [])
            stems_preview = ", ".join(stems[:4])
            if len(stems) > 4:
                stems_preview += f" (+{len(stems) - 4})"
            icon_cards.append(f"""
            <div class="card icon-card" data-name="{html.escape(icon_name)}" data-stems="{html.escape(' '.join(stems))}">
              <div class="icon-glyph">{svg_html}</div>
              <div class="icon-info">
                <div class="icon-name">{html.escape(icon_name)}</div>
                <div class="icon-stems" title="{html.escape(', '.join(stems))}">{html.escape(stems_preview or '—')}</div>
              </div>
            </div>
            """)

        theme_sections.append(f"""
        <div class="theme-pane" id="pane-{theme_id}" style="background-color: {colors['CANVAS']}; color: {colors['INK']};">
          <div class="theme-header" style="border-bottom: 1px solid {colors['LINE']};">
            <h2>{html.escape(b_name.upper())} &middot; <span style="color: {colors['ACCENT']};">{t_name.upper()}</span></h2>
            <p class="theme-desc">Canvas: <code>{colors['CANVAS']}</code> &bull; Ink: <code>{colors['INK']}</code> &bull; Accent: <span style="display:inline-block;width:12px;height:12px;background:{colors['ACCENT']};border-radius:50%;vertical-align:middle;margin:0 4px;"></span><code>{colors['ACCENT']}</code></p>
          </div>

          <section class="gallery-section">
            <h3 style="color: {colors['INK']};">Seed Drawings ({len(all_seeds)})</h3>
            <div class="drawings-grid">
              {''.join(drawing_cards)}
            </div>
          </section>

          <section class="gallery-section">
            <h3 style="color: {colors['INK']};">Icons ({len(lib_icons)})</h3>
            <div class="icons-grid">
              {''.join(icon_cards)}
            </div>
          </section>
        </div>
        """)

    theme_nav_buttons = []
    for idx, (b_name, t_name) in enumerate(themes_to_render):
        active = "active" if idx == 0 else ""
        t_id = f"{b_name}-{t_name}"
        theme_nav_buttons.append(
            f'<button class="tab-btn {active}" onclick="switchTheme(\'{t_id}\')">{html.escape(b_name)}:{html.escape(t_name)}</button>'
        )

    html_content = f"""<!DOCTYPE html>
<html lang="ka">
<head>
  <meta charset="utf-8">
  <title>Veasy Visual Vocabulary &middot; Icons & Drawings Contact Sheet</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #101113;
      color: #E0E2E6;
      line-height: 1.4;
    }}
    header.top-bar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: #1A1C20;
      border-bottom: 1px solid #2B2E35;
      padding: 14px 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 16px;
      justify-content: space-between;
    }}
    .title-group h1 {{ font-size: 18px; font-weight: 700; color: #FFF; }}
    .title-group p {{ font-size: 13px; color: #8F96A3; }}
    .controls {{ display: flex; align-items: center; gap: 12px; }}
    .tab-group {{ display: flex; background: #262930; border-radius: 8px; padding: 3px; gap: 2px; }}
    .tab-btn {{
      background: transparent;
      border: none;
      color: #A0A6B2;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .tab-btn.active {{
      background: #FF792E;
      color: #FFF;
    }}
    .search-box {{
      padding: 8px 14px;
      background: #262930;
      border: 1px solid #363A45;
      border-radius: 6px;
      color: #FFF;
      font-size: 13px;
      width: 260px;
    }}
    .theme-pane {{ display: none; padding: 32px 40px; min-height: 100vh; }}
    .theme-pane.active {{ display: block; }}
    .theme-header {{ margin-bottom: 28px; padding-bottom: 16px; }}
    .theme-header h2 {{ font-size: 26px; font-weight: 700; margin-bottom: 6px; }}
    .theme-desc {{ font-size: 14px; opacity: 0.75; }}
    .gallery-section {{ margin-bottom: 48px; }}
    .gallery-section h3 {{ font-size: 18px; font-weight: 700; margin-bottom: 18px; letter-spacing: 0.5px; text-transform: uppercase; }}
    
    .drawings-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 24px;
    }}
    .drawing-card {{
      border: 1px solid rgba(128,128,128,0.2);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      background: rgba(128,128,128,0.04);
    }}
    .drawing-preview {{
      padding: 12px;
      display: flex;
      justify-content: center;
      align-items: center;
      background: rgba(0,0,0,0.05);
    }}
    .drawing-preview svg {{ width: 100%; height: auto; border-radius: 8px; }}
    .card-meta {{ padding: 14px 16px; flex: 1; }}
    .card-title {{ font-size: 15px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }}
    .badge.stem {{ font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(128,128,128,0.18); font-weight: 600; }}
    .card-sub {{ font-size: 12px; opacity: 0.7; margin-bottom: 6px; }}
    .card-about {{ font-size: 13px; opacity: 0.85; line-height: 1.35; }}

    .icons-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 14px;
    }}
    .icon-card {{
      border: 1px solid rgba(128,128,128,0.15);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(128,128,128,0.03);
    }}
    .icon-glyph {{ flex-shrink: 0; display: flex; align-items: center; justify-content: center; }}
    .icon-info {{ overflow: hidden; }}
    .icon-name {{ font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .icon-stems {{ font-size: 11px; opacity: 0.65; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }}
  </style>
  <script>
    function switchTheme(id) {{
      document.querySelectorAll('.theme-pane').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      const targetPane = document.getElementById('pane-' + id);
      if (targetPane) targetPane.classList.add('active');
      event.target.classList.add('active');
    }}
    function filterCards(query) {{
      const q = query.trim().toLowerCase();
      document.querySelectorAll('.card').forEach(card => {{
        const name = (card.getAttribute('data-name') || '').toLowerCase();
        const motif = (card.getAttribute('data-motif') || '').toLowerCase();
        const stems = (card.getAttribute('data-stems') || '').toLowerCase();
        if (!q || name.includes(q) || motif.includes(q) || stems.includes(q)) {{
          card.style.display = '';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}
  </script>
</head>
<body>
  <header class="top-bar">
    <div class="title-group">
      <h1>Veasy Visual Vocabulary &middot; Contact Sheet</h1>
      <p>{len(lib_icons)} Lucide Icons &bull; {total_stems} Georgian Stems &bull; {len(all_seeds)} Seed Drawings &bull; 4 Brand Themes</p>
    </div>
    <div class="controls">
      <input type="text" class="search-box" placeholder="Filter by English or Georgian stem..." oninput="filterCards(this.value)">
      <div class="tab-group">
        {''.join(theme_nav_buttons)}
      </div>
    </div>
  </header>
  <main>
    {''.join(theme_sections)}
  </main>
  <script>
    // Activate first pane by default
    const firstPane = document.querySelector('.theme-pane');
    if (firstPane) firstPane.classList.add('active');
  </script>
</body>
</html>
"""
    target.write_text(html_content, encoding="utf-8")
    return {
        "html": str(target),
        "icons": len(lib_icons),
        "stems": total_stems,
        "drawings": len(all_seeds),
        "themes": [f"{b}:{t}" for b, t in themes_to_render],
    }
