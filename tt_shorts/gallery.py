"""`engine gallery`: builds a static HTML visual catalogue of every style, look, scene, and director.

One self-contained page for the owner, clients, and agents to browse, preview, and choose.
"""
from __future__ import annotations

import html
import json
import pathlib
import time

from tt_shorts import catalog, directors, formats, styles

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _svg_preview(title: str, subtitle: str, badge: str, bg: str = "#121316", accent: str = "#0ea5e9", text: str = "#f8fafc") -> str:
    """Generate a clean 9:16 vertical vector SVG style card preview."""
    safe_t = html.escape(title)
    safe_s = html.escape(subtitle)
    safe_b = html.escape(badge)
    return f"""<svg viewBox="0 0 270 480" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg" style="border-radius:12px;background:{bg};box-shadow:inset 0 0 0 1px rgba(255,255,255,0.08);">
  <defs>
    <linearGradient id="g_{safe_b}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0.05"/>
    </linearGradient>
  </defs>
  <rect width="270" height="480" rx="12" fill="{bg}"/>
  <rect x="12" y="12" width="246" height="456" rx="8" fill="url(#g_{safe_b})"/>
  <rect x="24" y="28" width="50" height="6" rx="3" fill="{accent}"/>
  <text x="24" y="60" fill="{text}" font-family="system-ui, sans-serif" font-size="11" font-weight="700" letter-spacing="1">{safe_b.upper()}</text>
  <line x1="24" y1="72" x2="246" y2="72" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
  
  <rect x="24" y="110" width="222" height="180" rx="8" fill="rgba(0,0,0,0.3)"/>
  <circle cx="135" cy="190" r="32" fill="{accent}" fill-opacity="0.2"/>
  <polygon points="128,175 148,190 128,205" fill="{accent}"/>
  
  <text x="24" y="330" fill="{text}" font-family="system-ui, sans-serif" font-size="16" font-weight="800">{safe_t}</text>
  <text x="24" y="352" fill="rgba(255,255,255,0.7)" font-family="system-ui, sans-serif" font-size="11">{safe_s}</text>
  
  <rect x="24" y="380" width="222" height="36" rx="6" fill="rgba(255,255,255,0.05)"/>
  <text x="36" y="403" fill="{accent}" font-family="system-ui, sans-serif" font-size="11" font-weight="600">Veasy Visual Frame</text>
  
  <rect x="24" y="432" width="70" height="14" rx="4" fill="rgba(255,255,255,0.08)"/>
  <text x="32" y="443" fill="rgba(255,255,255,0.5)" font-family="system-ui, sans-serif" font-size="9">1080 × 1920</text>
</svg>"""


def build_gallery(out_path: str | pathlib.Path | None = None) -> dict:
    """Build the standalone HTML gallery page."""
    t0 = time.time()
    out = pathlib.Path(out_path) if out_path else ROOT / "out" / "gallery.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    all_styles = styles.load_all()
    all_directors = directors.load_all()
    all_scenes = catalog.load_all()
    all_looks = [
        {"name": "editorial", "label": "Editorial Look", "desc": "Calm, strict modular grid, rising typography: hard news."},
        {"name": "kinetic", "label": "Kinetic Look", "desc": "Giant type, hard cuts, inverted color blocks: light news."},
        {"name": "cards", "label": "Cards Look", "desc": "Every scene a site-style story card: service news & explainers."},
    ]

    styles_html = []
    for s in all_styles:
        svg = _svg_preview(s["name_en"], s["name_ka"], s["category"], accent="#38bdf8")
        progs = ", ".join(s.get("programs", []))
        uses = html.escape(s.get("uses", ""))
        styles_html.append(f"""
        <div class="card" data-category="style" data-slug="{s['slug']}">
          <div class="preview-wrap">{svg}</div>
          <div class="card-body">
            <div class="badge-row">
              <span class="badge badge-accent">{html.escape(s['category'])}</span>
              <span class="badge badge-dim">{html.escape(s['engine'])}</span>
              <span class="badge badge-dim">{html.escape(s['palette'])}</span>
            </div>
            <h3 class="card-title">{html.escape(s['name_en'])}</h3>
            <p class="card-sub">{html.escape(s['name_ka'])} (<code>{s['slug']}</code>)</p>
            <p class="card-desc">{uses}</p>
            <div class="meta-row">
              <span>Programs: <strong>{html.escape(progs)}</strong></span>
            </div>
          </div>
        </div>
        """)

    looks_html = []
    for lk in all_looks:
        svg = _svg_preview(lk["label"], lk["name"], "LOOK", accent="#a855f7")
        looks_html.append(f"""
        <div class="card" data-category="look">
          <div class="preview-wrap">{svg}</div>
          <div class="card-body">
            <span class="badge badge-purple">LOOK</span>
            <h3 class="card-title">{html.escape(lk['label'])}</h3>
            <p class="card-desc">{html.escape(lk['desc'])}</p>
          </div>
        </div>
        """)

    scenes_html = []
    for sc_type, sc in all_scenes.items():
        svg = _svg_preview(sc.get("kicker") or sc_type.title(), sc_type, "BRUSH", accent="#10b981")
        example = html.escape(json.dumps(sc.get("example") or {}, ensure_ascii=False, indent=2))
        scenes_html.append(f"""
        <div class="card" data-category="scene">
          <div class="preview-wrap">{svg}</div>
          <div class="card-body">
            <span class="badge badge-green">BRUSH</span>
            <h3 class="card-title">{html.escape(sc_type)}</h3>
            <p class="card-sub">{html.escape(sc.get('kicker') or '')}</p>
            <p class="card-desc">{html.escape(sc.get('when') or 'General scene brush')}</p>
            <details class="code-details">
              <summary>View schema example</summary>
              <pre><code>{example}</code></pre>
            </details>
          </div>
        </div>
        """)

    directors_html = []
    for did, d in all_directors.items():
        d_name = d.get("label") or d.get("id") or did
        svg = _svg_preview(d_name, did, "DIRECTOR", accent="#f59e0b")
        directors_html.append(f"""
        <div class="card" data-category="director">
          <div class="preview-wrap">{svg}</div>
          <div class="card-body">
            <span class="badge badge-amber">DIRECTOR</span>
            <h3 class="card-title">{html.escape(d_name)} (<code>{did}</code>)</h3>
            <p class="card-desc">{html.escape(d.get('about') or '')}</p>
            <div class="meta-row">
              <span>Hooks: {len(d.get('hooks', []))} · Motifs: {len(d.get('motifs', []))}</span>
            </div>
          </div>
        </div>
        """)

    full_html = f"""<!DOCTYPE html>
<html lang="ka">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Veasy Visual Catalogue · ვიზუალური გალერეა</title>
  <style>
    :root {{
      --bg: #0b0d11;
      --card-bg: rgba(20, 24, 33, 0.7);
      --border: rgba(255, 255, 255, 0.08);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --purple: #a855f7;
      --green: #10b981;
      --amber: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 40px 24px;
    }}
    .header {{
      max-width: 1400px;
      margin: 0 auto 36px auto;
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
    }}
    .header h1 {{
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.5px;
      margin-bottom: 8px;
    }}
    .header p {{
      color: var(--text-muted);
      font-size: 16px;
      margin-bottom: 16px;
    }}
    .stats-bar {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .stat-pill {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
    }}
    .nav-tabs {{
      max-width: 1400px;
      margin: 0 auto 24px auto;
      display: flex;
      gap: 8px;
    }}
    .tab-btn {{
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 18px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
      transition: all 0.2s;
    }}
    .tab-btn.active, .tab-btn:hover {{
      background: var(--accent);
      color: #000;
      border-color: var(--accent);
    }}
    .section-title {{
      max-width: 1400px;
      margin: 32px auto 16px auto;
      font-size: 22px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .grid {{
      max-width: 1400px;
      margin: 0 auto 48px auto;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 20px;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.2s, border-color 0.2s;
      backdrop-filter: blur(12px);
    }}
    .card:hover {{
      transform: translateY(-4px);
      border-color: rgba(255, 255, 255, 0.2);
    }}
    .preview-wrap {{
      padding: 14px;
      background: rgba(0,0,0,0.2);
    }}
    .card-body {{
      padding: 16px;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .badge-row {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}
    .badge {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 2px 8px;
      border-radius: 4px;
    }}
    .badge-accent {{ background: rgba(56, 189, 248, 0.2); color: var(--accent); }}
    .badge-purple {{ background: rgba(168, 85, 247, 0.2); color: var(--purple); }}
    .badge-green {{ background: rgba(16, 185, 129, 0.2); color: var(--green); }}
    .badge-amber {{ background: rgba(245, 158, 11, 0.2); color: var(--amber); }}
    .badge-dim {{ background: rgba(255, 255, 255, 0.08); color: var(--text-muted); }}
    .card-title {{
      font-size: 17px;
      font-weight: 700;
    }}
    .card-sub {{
      font-size: 13px;
      color: var(--text-muted);
    }}
    .card-desc {{
      font-size: 13px;
      color: rgba(255, 255, 255, 0.8);
      flex: 1;
    }}
    .meta-row {{
      font-size: 12px;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
      padding-top: 8px;
      margin-top: 8px;
    }}
    .code-details {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 6px;
    }}
    .code-details summary {{
      cursor: pointer;
      color: var(--accent);
    }}
    .code-details pre {{
      background: rgba(0,0,0,0.5);
      padding: 8px;
      border-radius: 6px;
      margin-top: 6px;
      max-height: 180px;
      overflow: auto;
      font-size: 11px;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Veasy Visual Catalogue · ვიზუალური გალერეა</h1>
    <p>One front door: one static page of every style, look, scene brush, and director in the engine.</p>
    <div class="stats-bar">
      <div class="stat-pill">✨ {len(all_styles)} Named Film Styles</div>
      <div class="stat-pill">🎬 {len(all_looks)} Visual Looks</div>
      <div class="stat-pill">🎨 {len(all_scenes)} Scene Brushes</div>
      <div class="stat-pill">👤 {len(all_directors)} Directed Perspectives</div>
    </div>
  </div>

  <div class="nav-tabs">
    <button class="tab-btn active" onclick="filterCat('all')">All Options</button>
    <button class="tab-btn" onclick="filterCat('style')">Styles ({len(all_styles)})</button>
    <button class="tab-btn" onclick="filterCat('look')">Looks ({len(all_looks)})</button>
    <button class="tab-btn" onclick="filterCat('scene')">Scene Brushes ({len(all_scenes)})</button>
    <button class="tab-btn" onclick="filterCat('director')">Directors ({len(all_directors)})</button>
  </div>

  <h2 class="section-title">1. Named Film Styles ({len(all_styles)})</h2>
  <div class="grid" id="grid-styles">
    {''.join(styles_html)}
  </div>

  <h2 class="section-title">2. Visual Looks ({len(all_looks)})</h2>
  <div class="grid" id="grid-looks">
    {''.join(looks_html)}
  </div>

  <h2 class="section-title">3. Scene Brushes ({len(all_scenes)})</h2>
  <div class="grid" id="grid-scenes">
    {''.join(scenes_html)}
  </div>

  <h2 class="section-title">4. Directors ({len(all_directors)})</h2>
  <div class="grid" id="grid-directors">
    {''.join(directors_html)}
  </div>

  <script>
    function filterCat(cat) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      const cards = document.querySelectorAll('.card');
      cards.forEach(c => {{
        if (cat === 'all' || c.getAttribute('data-category') === cat) {{
          c.style.display = 'flex';
        }} else {{
          c.style.display = 'none';
        }}
      }});
    }}
  </script>
</body>
</html>"""

    out.write_text(full_html, encoding="utf-8")
    return {
        "file": str(out.resolve()),
        "styles": len(all_styles),
        "looks": len(all_looks),
        "scenes": len(all_scenes),
        "directors": len(all_directors),
        "took": round(time.time() - t0, 2),
    }
