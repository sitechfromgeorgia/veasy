"""The Edit Room page (<render>.room.html): every scene's still, words, timing, rhythm, pre-run cost, and copy-ready
`engine steer` commands.

Works identically for Remotion (`NewsShort`) and HyperFrames (`compose.py`) films, either from a finished render
(`<render>.mp4` / `<render>.json` / `<render>.props.json`) or directly from a story file (`stories/24835.json`,
`demo/film-partia.json`).
"""
import html
import json
import pathlib
import subprocess

from tt_shorts import brand as packs, catalog, compose, costs, motion_rules, probe, segments, speech, store

FPS = speech.FPS
EDITABLE_FIELDS = (
    "label", "headline", "kicker", "value", "unit", "sub", "note",
    "quote", "by", "role", "place", "term", "definition", "target", "change", "when",
    "lines", "items", "stops", "left", "right", "before", "after", "em",
)


def room_path(target) -> pathlib.Path:
    """Return `<render>.room.html` beside a render MP4/JSON or story JSON."""
    p = pathlib.Path(target).resolve()
    if p.suffix == ".json" and not p.name.endswith((".props.json", ".segments.json")) and not p.with_suffix(".mp4").exists():
        try:  # a story file with no render beside it: the page goes to the work folder, never into the repo
            raw = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "scenes" in raw and "narration" in raw:
                return store.work_dir("rooms") / f"{p.stem}.room.html"
        except (OSError, ValueError):
            pass
    for suffix in (".room.html", ".props.json", ".segments.json", ".json", ".mp4"):
        if p.name.endswith(suffix):
            stem = p.name[:-len(suffix)]
            return p.with_name(f"{stem}.room.html")
    return p.with_suffix(".room.html")


def stills_dir(room_html_path: pathlib.Path) -> pathlib.Path:
    stem = room_html_path.name[:-len(".room.html")] if room_html_path.name.endswith(".room.html") else room_html_path.stem
    d = room_html_path.with_name(f"{stem}-room")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _extract_video_stills(video_path: pathlib.Path, frames: list[int], out_dir: pathlib.Path) -> list[pathlib.Path]:
    """Extract settled PNG stills for each scene from an already-rendered MP4 via ffmpeg."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, f in enumerate(frames):
        png = out_dir / f"scene-{i:02d}.png"
        t = max(0.0, f / FPS)
        r = subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{t:.3f}", "-i", str(video_path),
                "-frames:v", "1", str(png),
            ],
            capture_output=True, check=False,
        )
        if r.returncode != 0 or not png.exists():
            _write_svg_still(png.with_suffix(".svg"), i, f, [], {})
            paths.append(png.with_suffix(".svg"))
        else:
            paths.append(png)
    return paths


def _write_svg_still(svg_path: pathlib.Path, scene_idx: int, frame: int, texts: list[tuple[str, str]],
                     colors: dict) -> pathlib.Path:
    """Write a deterministic 1080x1920 SVG frame preview when no MP4 is rendered yet."""
    canvas = colors.get("canvas", "#0B0D10")
    surface = colors.get("surface", "#13171D")
    ink = colors.get("ink", "#F3F4F6")
    muted = colors.get("muted", "#9CA3AF")
    accent = colors.get("accent", "#E11D48")
    lines_svg = []
    y = 420
    for field, val in texts[:6]:
        esc_f = html.escape(str(field))
        esc_v = html.escape(str(val)[:52])
        lines_svg.append(
            f'<text x="88" y="{y}" fill="{muted}" font-family="sans-serif" font-size="28" font-weight="500">{esc_f}</text>'
        )
        y += 58
        size = 76 if field in ("value", "headline") else 46
        lines_svg.append(
            f'<text x="88" y="{y}" fill="{ink}" font-family="sans-serif" font-size="{size}" font-weight="700">{esc_v}</text>'
        )
        y += 88
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="270" height="480">'
        f'<rect width="1080" height="1920" fill="{canvas}"/>'
        f'<rect x="64" y="248" width="952" height="1132" rx="16" fill="{surface}" stroke="{muted}" stroke-opacity="0.25" stroke-width="2"/>'
        f'<rect x="64" y="248" width="952" height="8" fill="{accent}"/>'
        f'<text x="88" y="328" fill="{muted}" font-family="monospace" font-size="30">SCENE {scene_idx} · FRAME {frame}</text>'
        f'{"".join(lines_svg)}'
        f'</svg>'
    )
    svg_path.write_text(svg, encoding="utf-8")
    return svg_path


def _scene_fields(scene: dict) -> list[tuple[str, str]]:
    """Return `[(field_name, formatted_value)]` for all editable fields present on `scene`."""
    out = []
    for k in EDITABLE_FIELDS:
        if k not in scene or scene[k] in (None, "", []):
            continue
        v = scene[k]
        if isinstance(v, (list, dict)):
            out.append((k, json.dumps(v, ensure_ascii=False)))
        else:
            out.append((k, str(v)))
    return out


def _primary_field(scene: dict) -> tuple[str, str]:
    """Choose the primary editable text slot of `scene` for the pre-filled `--set` command."""
    for pref in ("label", "headline", "kicker", "quote", "sub", "note", "place", "term"):
        if isinstance(scene.get(pref), str) and scene[pref].strip():
            return pref, scene[pref]
    if isinstance(scene.get("lines"), list) and scene["lines"]:
        return "lines[0]", str(scene["lines"][0])
    if isinstance(scene.get("items"), list) and scene["items"]:
        first = scene["items"][0]
        if isinstance(first, dict):
            for k in ("label", "title", "name", "text"):
                if k in first:
                    return f"items[0].{k}", str(first[k])
        return "items[0]", str(first)
    return "label", str(scene.get("label") or "")


def _spoken_slice(words: list[dict], start_sec: float, end_sec: float) -> list[dict]:
    """Words spoken during `[start_sec, end_sec)`."""
    out = []
    for w in words or []:
        mid = (float(w.get("start", 0)) + float(w.get("end", 0))) / 2.0
        if start_sec - 0.12 <= mid < end_sec + 0.08:
            out.append(w)
    return out


def _resolve_inputs(target, story_path=None, engine_override=None) -> dict:
    """Resolve `target` (an `.mp4`, `.json`, `.props.json`, or story `.json`) into `{story_path, story, props,
    render_mp4, film_engine, colors}`."""
    p = pathlib.Path(target).resolve()
    render_mp4 = None
    render_meta = {}
    props_data = None

    if p.suffix == ".mp4":
        render_mp4 = p
        meta_file = p.with_suffix(".json")
        props_file = p.with_suffix(".props.json")
        if meta_file.exists():
            render_meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if props_file.exists():
            props_data = json.loads(props_file.read_text(encoding="utf-8"))
        if not story_path and render_meta.get("story"):
            story_path = pathlib.Path(render_meta["story"])
    elif p.name.endswith(".props.json"):
        props_data = json.loads(p.read_text(encoding="utf-8"))
        stem = p.name[:-len(".props.json")]
        cand_mp4 = p.with_name(f"{stem}.mp4")
        if cand_mp4.exists():
            render_mp4 = cand_mp4
        cand_meta = p.with_name(f"{stem}.json")
        if cand_meta.exists():
            render_meta = json.loads(cand_meta.read_text(encoding="utf-8"))
            story_path = story_path or render_meta.get("story")
    elif p.suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
        if "scenes" in raw and isinstance(raw.get("scenes"), list) and "narration" in raw:
            story_path = p
            story = raw
            cand_mp4 = p.with_suffix(".mp4")
            if cand_mp4.exists():
                render_mp4 = cand_mp4
            cand_props = p.with_suffix(".props.json")
            if cand_props.exists():
                props_data = json.loads(cand_props.read_text(encoding="utf-8"))
        else:
            render_meta = raw
            story_path = pathlib.Path(story_path or raw.get("story") or p)
            if raw.get("file") and pathlib.Path(raw["file"]).exists():
                render_mp4 = pathlib.Path(raw["file"])
            if raw.get("props") and pathlib.Path(raw["props"]).exists():
                props_data = json.loads(pathlib.Path(raw["props"]).read_text(encoding="utf-8"))

    if story_path and pathlib.Path(story_path).exists():
        story_path = pathlib.Path(story_path).resolve()
        story = json.loads(story_path.read_text(encoding="utf-8"))
    elif props_data:
        story_path = p
        story = {
            "id": props_data.get("id", "film"),
            "brand": (props_data.get("brand") or {}).get("name", "tbilisi-today"),
            "category": props_data.get("category", "general"),
            "narration": " ".join(w.get("text", "") for w in (props_data.get("words") or [])),
            "scenes": props_data.get("scenes") or [],
        }
    else:
        raise FileNotFoundError(f"cannot resolve story or render props from {target}")

    b = packs.of(story)
    film_engine = engine_override or render_meta.get("film_engine") or compose.engine_for(story)[0]

    if props_data is None:
        words = speech.estimate_words(story.get("narration", ""))
        marks = speech.scene_frames(story, words)
        scenes = []
        for i, s in enumerate(story["scenes"]):
            scenes.append({**s, "from": marks[i], "duration": marks[i + 1] - marks[i]})
        props_data = {
            "id": story.get("id", "film"),
            "fps": FPS,
            "width": 1080,
            "height": 1920,
            "durationInFrames": marks[-1],
            "variant": "editorial",
            "theme": b.get("default_theme", "dark"),
            "transition": "cut",
            "outro": "card",
            "outroFrom": marks[-2] if len(marks) >= 2 else 0,
            "cta": story.get("cta") or "",
            "brand": packs.for_remotion(b),
            "style": {"variant": "editorial", "header": "bar", "footer": "ticker", "motif": "none"},
            "words": words,
            "scenes": scenes,
        }

    colors = (props_data.get("brand") or {}).get("colors") or b.get("colors") or {}
    return {
        "target": p,
        "story_path": story_path,
        "story": story,
        "props": props_data,
        "render_mp4": render_mp4,
        "render_meta": render_meta,
        "film_engine": film_engine,
        "brand": b,
        "colors": colors,
    }


def build_room_model(target, story_path=None, engine_override=None, out_html=None) -> dict:
    """Build the complete structured data model for `<render>.room.html`."""
    ctx = _resolve_inputs(target, story_path=story_path, engine_override=engine_override)
    story = ctx["story"]
    p = ctx["props"]
    scenes = p.get("scenes") or []
    words = p.get("words") or speech.estimate_words(story.get("narration", ""))
    motion = motion_rules.check(p)
    rows_by_scene = {r["scene"]: r for r in motion["timeline"]}
    findings_by_scene = {}
    for fnd in motion["findings"]:
        if fnd.get("scene") is not None:
            findings_by_scene.setdefault(fnd["scene"], []).append(fnd)

    seg_plan = segments.plan_remotion(p)
    seg_by_idx = {s["index"]: s for s in seg_plan["segments"]}
    settled_frames = probe.settled(scenes) if scenes else []

    html_file = pathlib.Path(out_html).resolve() if out_html else room_path(ctx["render_mp4"] or ctx["target"])
    s_dir = stills_dir(html_file)
    rel_dir = s_dir.name

    if ctx["render_mp4"] and pathlib.Path(ctx["render_mp4"]).exists():
        still_files = _extract_video_stills(pathlib.Path(ctx["render_mp4"]), settled_frames, s_dir)
    else:
        still_files = []
        for i, s in enumerate(scenes):
            f_num = settled_frames[i] if i < len(settled_frames) else int(s.get("from", 0))
            svg_p = s_dir / f"scene-{i:02d}.svg"
            _write_svg_still(svg_p, i, f_num, _scene_fields(s), ctx["colors"])
            still_files.append(svg_p)

    narration_chars = len(story.get("narration", ""))
    tts_dollars = round(float(costs.tts_usd(max(1, narration_chars // 3), round(len(words) and words[-1].get('end', 0) * costs.AUDIO_TOKENS_PER_SECOND or 0)) or 0), 4)
    total_frames = int(p.get("durationInFrames") or 0)
    total_secs = round(total_frames / FPS, 2)
    story_arg = str(ctx["story_path"])
    try:
        story_arg = ctx["story_path"].relative_to(pathlib.Path.cwd()).as_posix()
    except ValueError:
        story_arg = ctx["story_path"].as_posix()

    scene_cards = []
    for i, s in enumerate(scenes):
        row = rows_by_scene.get(i, {})
        seg = seg_by_idx.get(i, {})
        start_f = int(s.get("from", 0))
        dur_f = int(s.get("duration", 0))
        end_f = start_f + dur_f - 1
        start_s = round(start_f / FPS, 2)
        end_s = round((start_f + dur_f) / FPS, 2)
        dur_s = round(dur_f / FPS, 2)
        settled_f = settled_frames[i] if i < len(settled_frames) else start_f
        fields = _scene_fields(s)
        prim_k, prim_v = _primary_field(s)
        spoken = _spoken_slice(words, start_s, end_s)
        spoken_text = " ".join(w.get("text", "") for w in spoken)
        wps = round(len(spoken) / max(0.1, dur_s), 2)
        load_ratio = motion_rules.load(row) if row else 0.0
        leaves_f = row.get("leaves", end_f + 1)
        settled_s = row.get("settled", 0.5)
        quiet_tail_s = round(max(0.0, (leaves_f - start_f) / FPS - settled_s), 2)
        scene_findings = findings_by_scene.get(i, [])
        if any(f["hold"] for f in scene_findings):
            rhythm_state = "RUSHED (read hold)"
        elif scene_findings:
            rhythm_state = scene_findings[0]["rule"].upper()
        elif quiet_tail_s > 2.4 and s.get("type") != "end":
            rhythm_state = "SLACK (can --tighter)"
        elif load_ratio > 0.82:
            rhythm_state = "DENSE (can --breathe)"
        else:
            rhythm_state = "BALANCED"

        still_rel = f"{rel_dir}/{still_files[i].name}" if i < len(still_files) else ""
        esc_val = str(prim_v).replace('"', '\\"')
        cmd_base = f"python -m tt_shorts.engine steer {story_arg} --scene {i}"
        commands = {
            "dry_set": f'{cmd_base} --set {prim_k}="{esc_val}" --dry',
            "set": f'{cmd_base} --set {prim_k}="{esc_val}"',
            "tighter": f"{cmd_base} --tighter",
            "breathe": f"{cmd_base} --breathe",
            "land": f"{cmd_base} --land",
        }
        cost_before = {
            "text_edit": f"{dur_s:.1f} s of picture (scene {i}, frames {start_f}-{end_f}), $0.00",
            "timing_verb": f"{dur_s:.1f} s of picture (scene {i}, checked by motion_rules), $0.00",
            "narration_edit": f"new voice, every frame ({total_secs:.1f} s, all {len(scenes)} scenes, ~${tts_dollars:.4f} Gemini TTS or $0 preview)",
        }
        scene_cards.append({
            "index": i,
            "id": f"s{i}",
            "type": s.get("type", "scene"),
            "at": s.get("at", ""),
            "start_frame": start_f,
            "end_frame": end_f,
            "frames": dur_f,
            "settled_frame": settled_f,
            "start_sec": start_s,
            "end_sec": end_s,
            "duration_sec": dur_s,
            "sha": seg.get("sha", ""),
            "cached": bool(seg.get("cached")),
            "still": still_rel,
            "fields": fields,
            "primary_field": prim_k,
            "primary_value": prim_v,
            "spoken_text": spoken_text,
            "spoken_words": len(spoken),
            "words_per_sec": wps,
            "texts_timing": row.get("texts") or [],
            "load_ratio": load_ratio,
            "settled_sec": settled_s,
            "quiet_tail_sec": quiet_tail_s,
            "rhythm_state": rhythm_state,
            "findings": [f"{f['rule']}: {f['detail']}" for f in scene_findings],
            "cost": cost_before,
            "commands": commands,
        })

    return {
        "room_html": str(html_file),
        "stills_dir": str(s_dir),
        "story_id": story.get("id"),
        "story_path": str(ctx["story_path"]),
        "story_arg": story_arg,
        "render_mp4": str(ctx["render_mp4"]) if ctx["render_mp4"] else None,
        "brand": ctx["brand"]["name"],
        "film_engine": ctx["film_engine"],
        "total_frames": total_frames,
        "total_seconds": total_secs,
        "scene_count": len(scenes),
        "cached_count": len(seg_plan["hits"]),
        "dirty_count": len(seg_plan["misses"]),
        "tts_dollars": tts_dollars,
        "motion_holds": motion["holds"],
        "motion_warnings": motion["warnings"],
        "colors": ctx["colors"],
        "scenes": scene_cards,
    }


def render_room_html(model: dict) -> str:
    """Render the self-contained `<render>.room.html` page from `model`."""
    colors = model.get("colors") or {}
    canvas = colors.get("canvas", "#0B0D10")
    surface = colors.get("surface", "#13171D")
    ink = colors.get("ink", "#F3F4F6")
    muted = colors.get("muted", "#9CA3AF")
    accent = colors.get("accent", "#E11D48")
    rule = colors.get("rule", "#262C36")

    cards_html = []
    for sc in model["scenes"]:
        fields_rows = "".join(
            f'<tr><td class="k">{html.escape(k)}</td><td class="v">{html.escape(v)}</td></tr>'
            for k, v in sc["fields"]
        ) or '<tr><td colspan="2" class="muted">No editable slots</td></tr>'

        texts_rows = "".join(
            f'<li><code>{html.escape(t["text"])}</code> — {t["words"]}w · in at {t["in"]:.2f}s · '
            f'shown {t["shown"]:.2f}s (needs {t["need"]:.2f}s)</li>'
            for t in sc["texts_timing"]
        ) or "<li>No measured scene texts</li>"

        findings_html = ""
        if sc["findings"]:
            items = "".join(f"<li>{html.escape(x)}</li>" for x in sc["findings"])
            findings_html = f'<ul class="findings">{items}</ul>'

        cache_badge = "CACHED" if sc["cached"] else "NEEDS RENDER"
        cards_html.append(f"""
        <section class="scene-card" id="scene-{sc['index']}" data-scene="{sc['index']}" data-type="{html.escape(sc['type'])}">
          <header class="scene-head">
            <div>
              <span class="scene-num">SCENE {sc['index']} ({html.escape(sc['id'])})</span>
              <span class="scene-type">{html.escape(sc['type'])}</span>
              <span class="scene-rhythm">{html.escape(sc['rhythm_state'])}</span>
            </div>
            <div class="scene-meta">
              <span>{sc['start_sec']:.2f}s – {sc['end_sec']:.2f}s ({sc['duration_sec']:.2f}s · frames {sc['start_frame']}–{sc['end_frame']})</span>
              <span class="badge">{cache_badge} · {html.escape(sc['sha'][:8])}</span>
            </div>
          </header>
          <div class="scene-grid">
            <div class="still-col">
              <img src="{html.escape(sc['still'])}" alt="Scene {sc['index']} settled frame {sc['settled_frame']}" loading="lazy" />
              <div class="caption-small">Settled frame {sc['settled_frame']} ({round(sc['settled_frame'] / FPS, 2):.2f}s)</div>
            </div>
            <div class="info-col">
              <div class="panel">
                <h3>On-Screen Words (Editable Slots)</h3>
                <table class="slots-table">
                  <tbody>{fields_rows}</tbody>
                </table>
              </div>
              <div class="panel">
                <h3>Spoken Narration &amp; Anchor (<code>at="{html.escape(sc['at'])}"</code>)</h3>
                <p class="spoken">„{html.escape(sc['spoken_text'])}“</p>
                <div class="metrics">
                  <span>Spoken words: <strong>{sc['spoken_words']}</strong> ({sc['words_per_sec']:.2f} w/s)</span>
                  <span>Reading load: <strong>{sc['load_ratio']:.2f}x</strong></span>
                  <span>Settle: <strong>{sc['settled_sec']:.2f}s</strong></span>
                  <span>Quiet tail: <strong>{sc['quiet_tail_sec']:.2f}s</strong></span>
                </div>
                <ul class="text-timings">{texts_rows}</ul>
                {findings_html}
              </div>
              <div class="panel cost-panel">
                <h3>What a Change Will Cost Before It Runs</h3>
                <ul class="cost-list">
                  <li><strong>Text / slot change (<code>--set {html.escape(sc['primary_field'])}=...</code>):</strong> {html.escape(sc['cost']['text_edit'])} (only scene {sc['index']} redraws; other {model['scene_count'] - 1} scenes &amp; voice stay cached)</li>
                  <li><strong>Timing verb (<code>--tighter</code> / <code>--breathe</code> / <code>--land</code>):</strong> {html.escape(sc['cost']['timing_verb'])}</li>
                  <li><strong>Narration change (<code>--set narration=...</code>):</strong> {html.escape(sc['cost']['narration_edit'])} — a narration change moves later frames, so it stays a full render with a new voice (voice is never spliced by sentence).</li>
                </ul>
              </div>
              <div class="panel cmd-panel">
                <h3>Ready Commands to Copy</h3>
                <div class="cmd-row">
                  <span class="cmd-label">1. Check cost before running (<code>--dry</code>):</span>
                  <div class="cmd-box">
                    <code id="cmd-dry-{sc['index']}">{html.escape(sc['commands']['dry_set'])}</code>
                    <button type="button" onclick="copyCmd('cmd-dry-{sc['index']}', this)">Copy</button>
                  </div>
                </div>
                <div class="cmd-row">
                  <span class="cmd-label">2. Change on-screen text (redraws only scene {sc['index']}):</span>
                  <div class="cmd-box">
                    <code id="cmd-set-{sc['index']}">{html.escape(sc['commands']['set'])}</code>
                    <button type="button" onclick="copyCmd('cmd-set-{sc['index']}', this)">Copy</button>
                  </div>
                </div>
                <div class="cmd-row">
                  <span class="cmd-label">3. Plain rhythm verbs (checked by <code>motion_rules</code>):</span>
                  <div class="verb-grid">
                    <div class="cmd-box">
                      <code id="cmd-tight-{sc['index']}">{html.escape(sc['commands']['tighter'])}</code>
                      <button type="button" onclick="copyCmd('cmd-tight-{sc['index']}', this)">Copy</button>
                    </div>
                    <div class="cmd-box">
                      <code id="cmd-breathe-{sc['index']}">{html.escape(sc['commands']['breathe'])}</code>
                      <button type="button" onclick="copyCmd('cmd-breathe-{sc['index']}', this)">Copy</button>
                    </div>
                    <div class="cmd-box">
                      <code id="cmd-land-{sc['index']}">{html.escape(sc['commands']['land'])}</code>
                      <button type="button" onclick="copyCmd('cmd-land-{sc['index']}', this)">Copy</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        """)

    return f"""<!doctype html>
<html lang="ka">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Veasy Edit Room · {html.escape(str(model['story_id']))}</title>
  <style>
    :root {{
      --canvas: {canvas};
      --surface: {surface};
      --ink: {ink};
      --muted: {muted};
      --accent: {accent};
      --rule: {rule};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px 32px 64px;
      background: var(--canvas);
      color: var(--ink);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      line-height: 1.5;
    }}
    .top-bar {{
      max-width: 1360px;
      margin: 0 auto 28px;
      padding: 20px 24px;
      background: var(--surface);
      border: 1px solid var(--rule);
      border-top: 4px solid var(--accent);
      border-radius: 8px;
    }}
    .top-bar h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      font-weight: 700;
    }}
    .top-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 14px;
    }}
    .rule-banner {{
      padding: 12px 16px;
      border-left: 3px solid var(--accent);
      background: var(--canvas);
      font-size: 14px;
    }}
    .scene-card {{
      max-width: 1360px;
      margin: 0 auto 24px;
      background: var(--surface);
      border: 1px solid var(--rule);
      border-radius: 8px;
      overflow: hidden;
    }}
    .scene-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      padding: 14px 20px;
      border-bottom: 1px solid var(--rule);
    }}
    .scene-num {{ font-weight: 700; font-size: 16px; margin-right: 10px; }}
    .scene-type {{
      display: inline-block;
      padding: 2px 10px;
      border: 1px solid var(--rule);
      border-radius: 4px;
      font-family: monospace;
      font-size: 13px;
      margin-right: 10px;
    }}
    .scene-rhythm {{
      font-size: 13px;
      color: var(--muted);
      font-family: monospace;
    }}
    .scene-meta {{ color: var(--muted); font-size: 13px; display: flex; gap: 12px; align-items: center; }}
    .badge {{
      padding: 2px 8px;
      border: 1px solid var(--rule);
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
    }}
    .scene-grid {{
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 20px;
      padding: 20px;
    }}
    @media (max-width: 900px) {{
      .scene-grid {{ grid-template-columns: 1fr; }}
    }}
    .still-col img {{
      width: 100%;
      max-width: 260px;
      aspect-ratio: 9 / 16;
      object-fit: cover;
      border: 1px solid var(--rule);
      border-radius: 6px;
      display: block;
      background: var(--canvas);
    }}
    .caption-small {{ color: var(--muted); font-size: 12px; margin-top: 6px; font-family: monospace; }}
    .info-col {{ display: flex; flex-direction: column; gap: 14px; }}
    .panel {{
      padding: 14px 16px;
      background: var(--canvas);
      border: 1px solid var(--rule);
      border-radius: 6px;
    }}
    .panel h3 {{ margin: 0 0 10px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }}
    .slots-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    .slots-table td {{ padding: 6px 8px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
    .slots-table td.k {{ width: 140px; font-family: monospace; color: var(--muted); }}
    .slots-table td.v {{ font-weight: 600; }}
    .spoken {{ margin: 0 0 10px; font-size: 15px; }}
    .metrics {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px; color: var(--muted); margin-bottom: 8px; }}
    .text-timings, .cost-list, .findings {{ margin: 6px 0 0; padding-left: 20px; font-size: 13px; }}
    .cmd-row {{ margin-bottom: 10px; }}
    .cmd-label {{ display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }}
    .cmd-box {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 8px 10px;
      background: var(--surface);
      border: 1px solid var(--rule);
      border-radius: 4px;
      margin-bottom: 6px;
    }}
    .cmd-box code {{ font-family: monospace; font-size: 13px; word-break: break-all; }}
    .cmd-box button {{
      background: var(--canvas);
      color: var(--ink);
      border: 1px solid var(--rule);
      border-radius: 4px;
      padding: 4px 10px;
      cursor: pointer;
      font-size: 12px;
      flex-shrink: 0;
    }}
  </style>
</head>
<body>
  <header class="top-bar">
    <h1>Veasy Edit Room · Story {html.escape(str(model['story_id']))}</h1>
    <div class="top-meta">
      <span>Brand: <strong>{html.escape(model['brand'])}</strong></span>
      <span>Engine: <strong>{html.escape(model['film_engine'])}</strong></span>
      <span>Duration: <strong>{model['total_seconds']:.1f}s ({model['total_frames']} frames @ 30fps)</strong></span>
      <span>Scenes: <strong>{model['scene_count']}</strong> ({model['cached_count']} cached, {model['dirty_count']} unrendered)</span>
      <span>Story: <code>{html.escape(model['story_arg'])}</code></span>
    </div>
    <div class="rule-banner">
      <strong>Pre-Run Cost Guarantee:</strong> Changing a scene's on-screen text (<code>--set field="..."</code>) or timing rhythm (<code>--tighter</code>, <code>--breathe</code>, <code>--land</code>) redraws <strong>only the touched scene(s)</strong> at <strong>$0.00</strong> voice cost and stitches cached segments with FFmpeg. Changing spoken <code>narration</code> moves later word timestamps and scene boundaries, so it stays a <strong>full render with a new continuous voice</strong> ("new voice, every frame" — voice is never spliced by sentence). Pass <code>--dry</code> to verify exact seconds and cost before running.
    </div>
  </header>
  <main>
    {"".join(cards_html)}
  </main>
  <script>
    function copyCmd(id, btn) {{
      const text = document.getElementById(id).innerText;
      navigator.clipboard.writeText(text);
      const prev = btn.innerText;
      btn.innerText = "Copied";
      setTimeout(() => {{ btn.innerText = prev; }}, 1200);
    }}
  </script>
</body>
</html>
"""


def write_room(target, story_path=None, engine_override=None, out_html=None) -> dict:
    """Build the room model, write `<render>.room.html`, and return the summary dict."""
    model = build_room_model(target, story_path=story_path, engine_override=engine_override, out_html=out_html)
    out_file = pathlib.Path(model["room_html"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(render_room_html(model), encoding="utf-8")
    return model
