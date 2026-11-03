"""Veasy's side of a film composed for the HyperFrames engine (docs/plan-v2.md; phase 0 spike): everything in a
HyperFrames project that code owns, for any brand pack, so the agent composes scenes and nothing else.

    python tools/compose_scaffold.py compose/24835 [--brand sitech] [--theme light] [--out DIR]
                                                         # -> out/compose/24835-<pack>[-<theme>]/

Copies the agent's pack-neutral source (index.html, compositions/s*.html, beats.json: colors only as var(--token))
into the project folder and writes beside it:
    assets/brand.css             the tokens of the pack's theme (its default, or --theme: brand.json themes) as CSS
                                 variables and its font as "Brand"
    frame.md                     the pack's design spec (tt_shorts/frame_md.py)
    timing.json                  the voice's words (silent engine here), the chapters and beats resolved to seconds,
                                 the film's length, the facts the chrome shows, the map of the place
    assets/fonts/brand-*.woff2   the pack's four weights (git-ignored: copied from the pack)
    assets/vendor/gsap.min.js    GSAP 3.15.0 from the pinned HyperFrames package (git-ignored; no CDN at render)
    assets/icons/<name>.svg      the Lucide icons the beat sheet names, in the pack's ink
    assets/qr.svg                the story's QR code
    assets/media/<id>.<ext>      the story's pictures from its assets ledger (tt_shorts/assets.py), local files only,
    assets/media.json            with each one's label and credit, which scene it belongs to, and the ledger itself
    compositions/chrome.html     locked chrome: the pack's mark, date, weekday · time · category, the chapter bar,
                                 the meter wipes at the chapter cuts, the ticker, the source line, link and footer,
                                 the end card (the pack's logo, the QR, the link, the call to action on its button)
    compositions/captions.html   locked captions: tt_shorts/captions.py's layout (one size, pages, bridged gaps),
                                 drawn as Remotion draws them; keywords from the beat sheet in inverted ink

Every text element carries data-probe (header, footer, ticker, captions) as the Remotion engine's do, so the layout
probe reads a composed page with the same rules. The phase 2 command (`engine compose scaffold`) grows from this.
"""
import argparse
import html
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tt_shorts import assets, brand, frame_md, icons, meta, props, speech  # noqa: E402

FPS = speech.FPS
W, H, SIDE = 1080, 1920, 64
WIPE = 0.34  # seconds the meter bars take to rise (and again to fall) around a chapter cut
BARS = 12
GSAP = ROOT / "compose" / "node_modules" / "hyperframes" / "dist" / "vendor" / "npm" / "gsap@3.15.0" / "dist" / "gsap.min.js"


def esc(s):
    return html.escape(str(s), quote=True)


def font_faces(prefix="assets/fonts"):
    return "\n".join(
        f"@font-face {{ font-family: \"Brand\"; font-weight: {w}; font-style: normal; font-display: block; "
        f"src: url('{prefix}/brand-{w}.woff2') format('woff2'); }}" for w in brand.FONT_WEIGHTS)


def resolve(beats, words):
    """The beat sheet's anchors -> seconds, in order (speech.anchor: each search starts after the previous one)."""
    out, after = [], 0
    for b in beats:
        t, _ = speech.anchor(words, b["at"], after)
        after = next(i for i, w in enumerate(words) if w["start"] == t) + 1  # the next beat may share words
        out.append({**b, "t": round(t, 3)})
    return out


def timing(project, story_path, sheet, theme="default"):
    work, p = props.build(str(story_path), "cards", "silent", music="off", transition="cut", theme=theme)
    words = p["words"]
    keys = {speech.norm(k) for k in sheet.get("keywords", [])}
    dur = p["durationInFrames"] / FPS
    chapters = []
    for i, ch in enumerate(sheet["chapters"]):
        t = 0.0 if i == 0 else round(speech.anchor(words, ch["at"])[0] - 0.08, 3)
        chapters.append({"n": i + 1, "of": len(sheet["chapters"]), "title": ch["title"], "from": t})
    end = round(speech.anchor(words, sheet["end"]["at"])[0] - 0.08, 3)
    for a, b in zip(chapters, chapters[1:] + [{"from": end}]):
        a["to"] = b["from"]
    beats = resolve(sheet["beats"], words)
    beats[0]["t"] = 0.0  # frame 0 is the hook
    gaps = [round(b["t"] - a["t"], 2) for a, b in zip(beats, beats[1:])]
    where = next((s for s in p["scenes"] if s.get("map")), None)
    return {
        "about": "Written by tools/compose_scaffold.py from the story, the voice and beats.json: do not edit.",
        "story": p["id"], "brand": p["brand"]["name"], "theme": p["theme"], "engine": "silent", "fps": FPS,
        "frames": p["durationInFrames"], "duration": round(dur, 3), "width": W, "height": H,
        "words": [{"i": i, "text": w["text"], "start": w["start"], "end": w["end"],
                   "keyword": speech.norm(w["text"]) in keys} for i, w in enumerate(words)],
        "chapters": chapters, "end": end, "wipes": [c["from"] for c in chapters[1:]] + [end],
        "beats": beats, "gaps": {"min": min(gaps), "max": max(gaps), "over_3s": [
            beats[i + 1]["id"] for i, g in enumerate(gaps) if g > 3 and beats[i + 1]["id"] != "cta"]},
        "laneA": [{"type": s["type"], "from": round(s["from"] / FPS, 3), "to": round((s["from"] + s["duration"]) / FPS, 3)}
                  for s in p["scenes"]],
        "facts": {"date": p["date"], "category": p["category"], "sources": p["sources"], "sourcesLine": p["sourcesLine"],
                  "url": p["url"], "cta": p["cta"], "previewNote": p["previewNote"]},
        "map": {k: where["map"][k] for k in ("viewBox", "focus", "pins", "level", "credit")} if where else None,
    }, p, work


# ---------------------------------------------------------------- locked chrome

def tmark(size, b):
    c = b["colors"]
    from_ts = (ROOT / "remotion" / "src" / "brand.ts").read_text(encoding="utf-8")
    path = from_ts.split('T_PATH =\n  "', 1)[1].split('"', 1)[0]
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 512 512"><rect width="512" height="512" rx="112" '
            f'fill="{c["markBg"]}"/><g transform="translate(0,512) scale(0.1,-0.1)"><path d="{path}" fill="{c["markInk"]}"/>'
            f'</g><circle cx="323" cy="295" r="34" fill="{c["accent"]}"/></svg>')


def wordmark(b, size):
    w = b["wordmark"]
    i = w["text"].find(w.get("accent") or "\0")
    t = esc(w["text"]) if i < 0 else (esc(w["text"][:i]) + f'<span class="acc">{esc(w["accent"])}</span>'
                                      + esc(w["text"][i + len(w["accent"]):]))
    return f'<span class="wordmark" style="font-size:{size}px">{t}</span>'


def logo(b, project, place="header"):
    """The pack's logo as Remotion's Logo draws it: tmark = the mark next to (header) or above (end) the wordmark;
    svg = the pack's own files (they carry the name)."""
    if b["logo"]["kind"] == "svg":
        shutil.copy(b["_logo"][place], project / "assets" / f"logo-{place}.svg")
        size = "height:88px" if place == "header" else "height:340px"  # the end logo fits the band above the QR
        return f'<div class="logo-{place}"><img src="assets/logo-{place}.svg" style="{size};display:block" alt=""></div>'
    if place == "header":
        return f'<div class="logo-header">{tmark(88, b)}{wordmark(b, 44)}</div>'
    return f'<div class="logo-end">{tmark(220, b)}{wordmark(b, 84)}</div>'


def end_card(t, b, project):
    """The end card (Lane A's "end" scene): the pack's logo, the story's QR and link, its call to action on the
    pack's button. In at the end mark; the QR and the CTA land on their beats when the beat sheet names them."""
    f = t["facts"]
    at = {x["id"]: x["t"] for x in t["beats"]}
    e = t["end"]
    q, k = at.get("end-link", e + 1.3), at.get("cta", e + 2.9)
    body = f"""
    <div id="chrome-end" class="end" data-probe="scene">{logo(b, project, "end")}
      <div id="chrome-qr" class="qr"><img src="assets/qr.svg" alt=""></div>
      <div id="chrome-link" class="link">{esc(f['url'])}</div>
      <div id="chrome-cta" class="cta">{esc(f['cta'])}</div></div>"""
    js = ['tl.set("#chrome-end", { opacity: 0 }, 0);',
          f'tl.set("#chrome-end", {{ opacity: 1 }}, {e:.3f});',
          f'tl.fromTo("#chrome-end .logo-end", {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.6)" }}, {e + 0.08:.3f});',
          f'tl.fromTo("#chrome-qr", {{ opacity: 0, scale: 0.85 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "expo.out" }}, {q:.3f});',
          f'tl.fromTo("#chrome-link", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.35, ease: "expo.out" }}, {q + 0.1:.3f});',
          f'tl.fromTo("#chrome-cta", {{ opacity: 0, scale: 0.8, y: 30 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.45, ease: "back.out(1.7)" }}, {k + 0.06:.3f});']
    return body, js


def chrome(t, b, project):
    c, f = b["colors"], t["facts"]
    dur, chapters = t["duration"], t["chapters"]
    seg_w = (W - 2 * SIDE - 8 * (len(chapters) - 1)) / len(chapters)
    segs, labels = [], []
    for i, ch in enumerate(chapters):
        x = SIDE + i * (seg_w + 8)
        segs.append(f'<div class="seg" style="left:{x:.1f}px;width:{seg_w:.1f}px"><div id="chrome-fill-{i}" class="fill"></div></div>')
        labels.append(f'<div id="chrome-ch-{i}" class="chlabel" data-probe="header"><b>{ch["n"]:02d} / {ch["of"]:02d}</b>'
                      f'<span>{esc(ch["title"])}</span></div>')
    bars = "".join(f'<div class="bar" id="chrome-bar-{w}-{k}" style="left:{SIDE + k * ((W - 2 * SIDE + 8) / BARS):.1f}px;'
                   f'width:{(W - 2 * SIDE + 8) / BARS - 8:.1f}px;background:{c["ink"] if k % 3 else c["muted"]}"></div>'
                   for w in range(len(t["wipes"])) for k in range(BARS))
    row = "  ·  ".join([f["category"], f["date"]["date"], *f["sources"], b["label"]])
    ticker = esc("  ·  ".join([row] * 4))
    footer_strong = f'<b>{esc(b["footer"]["strong"])}</b>' if b["footer"].get("strong") else ""
    note = f'<div class="note" data-probe="ticker">{esc(f["previewNote"])}</div>' if f.get("previewNote") else ""
    js = [f"const tl = gsap.timeline({{ paused: true }});"]
    for i, ch in enumerate(chapters):  # the current chapter's segment fills with its time; the dot is its head
        js.append(f'tl.fromTo("#chrome-fill-{i}", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {ch["to"] - ch["from"]:.3f}, ease: "none" }}, {ch["from"]:.3f});')
        if i == 0:  # frame 0 is the thumbnail: the first chapter is already there
            js.append('tl.set("#chrome-ch-0", { opacity: 1 }, 0);')
        else:
            js.append(f'tl.fromTo("#chrome-ch-{i}", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "expo.out", immediateRender: false }}, {ch["from"] + 0.05:.3f});')
        js.append(f'tl.to("#chrome-ch-{i}", {{ opacity: 0, duration: 0.15, ease: "power2.in" }}, {ch["to"] - 0.15:.3f});')
        x0 = SIDE + i * (seg_w + 8)
        js.append(f'tl.fromTo("#chrome-dot", {{ x: {x0 - 10:.1f} }}, {{ x: {x0 + seg_w - 10:.1f}, duration: {ch["to"] - ch["from"]:.3f}, ease: "none", immediateRender: {str(i == 0).lower()} }}, {ch["from"]:.3f});')
    js.append(f'tl.to("#chrome-dot", {{ opacity: 0, duration: 0.2 }}, {t["end"]:.3f});')
    # the meter wipe: the bars rise like an equaliser (each to its own height, then all the way), cover the scene
    # band at the cut for a moment (the scenes swap under them) and fall away upward, left to right
    rng = [0.42, 0.78, 0.55, 0.95, 0.6, 0.86, 0.38, 0.7, 0.92, 0.5, 0.8, 0.64]
    js.append('tl.set(".bar", { scaleY: 0, transformOrigin: "50% 100%" }, 0);')
    for w, at in enumerate(t["wipes"]):
        for k in range(BARS):
            el = f"#chrome-bar-{w}-{k}"
            a = at - WIPE - 0.04 + 0.016 * k
            rise = at - 0.02 - (a + 0.14)
            js.append(f'tl.fromTo("{el}", {{ scaleY: 0, transformOrigin: "50% 100%" }}, {{ scaleY: {rng[k]}, duration: 0.14, ease: "power2.out", immediateRender: false }}, {a:.3f});')
            js.append(f'tl.to("{el}", {{ scaleY: 1.01, duration: {rise:.3f}, ease: "power2.inOut" }}, {a + 0.14:.3f});')
            js.append(f'tl.set("{el}", {{ transformOrigin: "50% 0%" }}, {at + 0.02:.3f});')
            js.append(f'tl.to("{el}", {{ scaleY: 0, duration: 0.3, ease: "power3.in" }}, {at + 0.02 + 0.016 * k:.3f});')
    js.append(f'tl.fromTo("#chrome-tickrow", {{ x: 0 }}, {{ x: -{2.2 * FPS * dur:.0f}, duration: {dur:.3f}, ease: "none" }}, 0);')
    end_body, end_js = end_card(t, b, project)
    js += end_js
    js.append('window.__timelines["chrome"] = tl;')
    css = f"""
    {font_faces()}
    #root {{ position: absolute; inset: 0; font-family: "Brand", sans-serif; color: {c['ink']}; }}
    #root .logo-header {{ position: absolute; left: {SIDE}px; top: 80px; height: 88px; display: flex; align-items: center; gap: 24px; }}
    #root .end {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; }}
    #root .logo-end {{ position: absolute; left: 0; right: 0; top: 300px; display: flex; flex-direction: column; align-items: center; gap: 24px; }}
    #root .qr {{ position: absolute; left: 380px; top: 690px; width: 320px; height: 320px; border-radius: 14px; overflow: hidden; }}
    #root .qr img {{ width: 320px; height: 320px; display: block; }}
    #root .link {{ position: absolute; left: 140px; right: 140px; top: 1036px; text-align: center; font-weight: 700; font-size: 40px; line-height: 1.2; white-space: nowrap; }}
    #root .cta {{ position: absolute; left: 156px; width: 768px; top: 1128px; height: 88px; border-radius: 999px; background: {c['accent']}; color: {c['onAccent']};
      display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 40px; line-height: 1; white-space: nowrap; }}
    #root .wordmark {{ font-weight: 700; color: {c['ink']}; white-space: nowrap; }}
    #root .acc {{ color: {c['accent']}; }}
    #root .date {{ position: absolute; right: {SIDE}px; top: 80px; text-align: right; }}
    #root .date .d {{ font-weight: 700; font-size: 40px; line-height: 1.2; }}
    #root .date .m {{ font-weight: 400; font-size: 30px; line-height: 1.4; color: {c['muted']}; }}
    #root .seg {{ position: absolute; top: 204px; height: 6px; border-radius: 3px; background: {c['lineStrong']}; overflow: hidden; }}
    #root .fill {{ position: absolute; inset: 0; background: {c['ink']}; transform-origin: 0 50%; }}
    #root .dot {{ position: absolute; left: 0; top: 197px; width: 20px; height: 20px; border-radius: 10px; background: {c['accent']}; }}
    #root .chlabel {{ position: absolute; left: {SIDE}px; top: 222px; display: flex; gap: 16px; align-items: baseline; font-size: 28px; line-height: 1.2; opacity: 0; white-space: nowrap; }}
    #root .chlabel b {{ font-weight: 700; color: {c['ink']}; }}
    #root .chlabel span {{ font-weight: 500; color: {c['muted']}; }}
    #root .bar {{ position: absolute; top: 248px; height: 1132px; border-radius: 14px; }}
    #root .ticker {{ position: absolute; left: 0; right: 0; top: 1580px; height: 180px; overflow: hidden; }}
    #root .tickrow {{ position: absolute; top: 44px; left: 0; white-space: pre; font-weight: 700; font-size: 128px; line-height: 1; color: {c['ticker']}; }}
    #root .note {{ position: absolute; right: {SIDE}px; top: 1580px; font-weight: 600; font-size: 28px; line-height: 1; padding: 11px 20px 13px; border-radius: 999px; border: 2px solid {c['lineStrong']}; white-space: nowrap; }}
    #root .footer {{ position: absolute; left: {SIDE}px; right: {SIDE}px; top: 1768px; border-top: 2px solid {c['line']}; padding-top: 16px; }}
    #root .footer .src {{ font-weight: 400; font-size: 28px; line-height: 1.4; color: {c['muted']}; white-space: nowrap; overflow: hidden; }}
    #root .footer .row {{ display: flex; justify-content: space-between; align-items: baseline; }}
    #root .footer .url {{ font-weight: 700; font-size: 36px; line-height: 1.4; white-space: nowrap; }}
    #root .footer .pack {{ font-size: 28px; line-height: 1.4; color: {c['muted']}; white-space: nowrap; }}
    #root .footer .pack b {{ font-weight: 700; color: {c['ink']}; }}"""
    body = f"""
    <div data-probe="header">{logo(b, project)}</div>{end_body}
    <div class="date" data-probe="header"><div class="d">{esc(f['date']['date'])}</div>
      <div class="m">{esc(f['date']['weekday'])} · {esc(f['date']['time'])} · {esc(f['category'])}</div></div>
    {''.join(segs)}
    <div id="chrome-dot" class="dot"></div>
    {''.join(labels)}
    {bars}
    <div class="ticker" data-probe="ticker" data-layout-ignore><div id="chrome-tickrow" class="tickrow">{ticker}</div></div>
    {note}
    <div class="footer" data-probe="footer"><div class="src">{esc(f['sourcesLine'])}</div>
      <div class="row"><span class="url">{esc(f['url'])}</span><span class="pack">{esc(b['footer']['text'])}{footer_strong}</span></div></div>"""
    return locked("chrome", css, body, js)


def captions_html(cap, t, b):
    """props.captions (captions.py) as HyperFrames DOM + timeline: Captions.tsx's page design, frame for frame."""
    c = b["colors"]
    words = t["words"]
    key = {(w["text"], round(w["start"], 3)) for w in words if w["keyword"]}
    size, lh, band, pad = cap["size"], cap["lineHeight"], cap["band"], cap["pad"]
    row = size * lh
    box_h = row * 2 + 28
    pages, js = [], ["const tl = gsap.timeline({ paused: true });"]
    allw = [w for l in cap["lines"] for w in l["words"]]
    n = 0
    for k, p in enumerate(cap["pages"]):
        lines = []
        for li in p["lines"]:
            ws = cap["lines"][li]["words"]
            spans = []
            for j, w in enumerate(ws):
                wid = f"cap-w{n}"
                n += 1
                is_key = (w["text"], round(w["from"], 3)) in key
                spans.append(f'<span id="{wid}" class="w{" k" if is_key else ""}"{"" if j < len(ws) - 1 else " style=\"margin-right:0\""}>'
                             f'{"<i class=\"kb\"></i>" if is_key else ""}<em>{esc(w["text"])}</em><i class="u"></i></span>')
                nxt = [x["from"] for x in allw if x["from"] > w["from"]]  # the next word anywhere, not only on this line
                until = min([w["to"] + 0.35] + nxt[:1]) if j + 1 == len(ws) else ws[j + 1]["from"]
                js.append(f'tl.set("#{wid}", {{ color: "{c["ink"]}" }}, {max(0, w["from"] - 0.04):.3f});')
                if is_key:
                    js.append(f'tl.fromTo("#{wid} .kb", {{ scaleX: 0.6, opacity: 0 }}, {{ scaleX: 1, opacity: 1, duration: 0.12, ease: "power3.out" }}, {max(0, w["from"] - 0.04):.3f});')
                    js.append(f'tl.set("#{wid} em", {{ color: "{c["canvas"]}" }}, {max(0, w["from"] - 0.04):.3f});')
                js.append(f'tl.fromTo("#{wid} .u", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.12, ease: "power3.out" }}, {max(0, w["from"] - 0.04):.3f});')
                js.append(f'tl.set("#{wid} .u", {{ scaleX: 0 }}, {until:.3f});')
            lines.append(f'<div class="line">{"".join(spans)}</div>')
        pid = f"cap-p{k}"
        pages.append(f'<div id="{pid}" class="page"><div class="inner">{"".join(lines)}</div></div>')
        js.append(f'tl.fromTo("#{pid}", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.14, ease: "power3.out" }}, {p["start"]:.3f});')
        js.append(f'tl.to("#{pid}", {{ opacity: 0, duration: 0.18, ease: "power1.in" }}, {max(p["start"] + 0.2, p["end"] - 0.18):.3f});')
        js.append(f'tl.set("#{pid}", {{ opacity: 0 }}, {p["end"]:.3f});')
    # the box: in after a real silence, out where a page ends without the next one following at once
    runs, cur = [], None
    for p in cap["pages"]:
        if cur and p["start"] - cur[1] <= 0.05:
            cur[1] = p["end"]
        else:
            cur = [p["start"], p["end"]]
            runs.append(cur)
    for a, z in runs:
        js.append(f'tl.fromTo("#cap-box", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2, ease: "none" }}, {a:.3f});')
        js.append(f'tl.to("#cap-box", {{ opacity: 0, duration: 0.18, ease: "none" }}, {max(a + 0.2, z - 0.18):.3f});')
    js.append('window.__timelines["captions"] = tl;')
    css = f"""
    {font_faces()}
    #root {{ position: absolute; inset: 0; font-family: "Brand", sans-serif; }}
    #cap-box {{ position: absolute; left: {W - 940}px; width: {band}px; top: {1552 - box_h:.1f}px; height: {box_h:.1f}px;
      background: rgba({int(c['canvas'][1:3], 16)},{int(c['canvas'][3:5], 16)},{int(c['canvas'][5:7], 16)},0.8);
      border: 2px solid {c['line']}; border-radius: 14px; opacity: 0; }}
    #root .page {{ position: absolute; left: {W - 940}px; width: {band}px; top: {1552 - box_h:.1f}px; height: {box_h:.1f}px;
      display: flex; align-items: center; justify-content: center; padding: 0 {pad}px; opacity: 0; }}
    #root .line {{ font-weight: 700; font-size: {size}px; line-height: {lh}; white-space: nowrap; text-align: center; }}
    #root .w {{ position: relative; display: inline-block; margin-right: 0.27em; color: {c['waiting']}; }}
    #root .w em {{ position: relative; font-style: normal; }}
    #root .w .u {{ position: absolute; left: 0; right: 0; bottom: -4px; height: 5px; border-radius: 3px; background: {c['accent']};
      transform-origin: left; }}
    #root .w .kb {{ position: absolute; left: -0.14em; right: -0.14em; top: 0.1em; bottom: 0.02em; border-radius: 8px;
      background: {c['ink']}; opacity: 0; }}"""
    body = f'<div id="cap-box"></div><div data-probe="captions">{"".join(pages)}</div>'
    return locked("captions", css, body, js)


def locked(cid, css, body, js):
    return f"""<!-- LOCKED: written by tools/compose_scaffold.py from the story and its timing. Place its host in index.html;
     never edit, restyle, cover or remove it (frame.md, Locked Chrome). -->
<template>
  <style>{css}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="{W}" data-height="{H}">{body}
  </div>
  <script>
    {chr(10).join('    ' + l for l in js).lstrip()}
  </script>
</template>
"""


def icon_svg(name, color, stroke=2):
    parts = []
    for tag, attrs in icons.nodes(name):
        a = " ".join(f'{k}="{esc(v)}"' for k, v in attrs.items())
        parts.append(f"<{tag} {a}/>")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{"".join(parts)}</svg>\n')


MAP_W, MAP_H = 952, 600  # the map's box in a scene, px


def map_box(box, w=MAP_W, h=MAP_H):
    """A viewBox [x, y, w, h] around a map box [x0, y0, x1, y1] with the scene box's aspect ratio."""
    x0, y0, x1, y1 = box
    k = max((x1 - x0) / w, (y1 - y0) / h)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return [round(cx - w * k / 2, 1), round(cy - h * k / 2, 1), round(w * k, 1), round(h * k, 1)]


def map_svg(m, vb, c, tint):
    """Georgia (tt_shorts/geo.py's projection) seen through viewBox vb, drawn as map.tsx draws it: the land in a faint
    ink, the region in a quiet ink tint, rivers, dashed borders, the region outlined; strokes in screen px."""
    u = vb[2] / MAP_W  # map units per screen px
    regions = "".join(f'<path d="{r}" fill="{c["ink"]}" fill-opacity="{0.18 * tint:.2f}"/>' for r in m["regions"])
    outlines = "".join(f'<path d="{r}" fill="none" stroke="{c["ink"]}" stroke-width="{4 * u:.1f}" stroke-linejoin="round" '
                       f'opacity="{tint}"/>' for r in m["regions"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(map(str, vb))}" width="{MAP_W}" height="{MAP_H}">'
            f'<defs><clipPath id="land"><path d="{m["land"]}"/></clipPath></defs>'
            f'<path d="{m["land"]}" fill="{c["ink"]}" fill-opacity="0.05"/>{regions}'
            f'<path d="{m["rivers"]}" fill="none" stroke="{c["ink"]}" stroke-opacity="0.3" stroke-width="{2.5 * u:.1f}" '
            f'stroke-linejoin="round" stroke-linecap="round" clip-path="url(#land)"/>'
            f'<path d="{m["borders"]}" fill="none" stroke="{c["lineStrong"]}" stroke-width="{2 * u:.1f}" '
            f'stroke-dasharray="{8 * u:.1f} {6 * u:.1f}"/>{outlines}'
            f'<path d="{m["land"]}" fill="none" stroke="{c["ink"]}" stroke-width="{3 * u:.1f}" stroke-linejoin="round"/></svg>\n')


def brand_css(b):
    """The pack's tokens as CSS variables and its font as "Brand": the only place a scene gets a color or a face."""
    c = b["colors"]
    names = {"canvas": "canvas", "panel": "panel", "ink": "ink", "muted": "muted", "accent": "accent", "line": "line",
             "lineStrong": "line-strong", "grid": "grid", "ticker": "ticker", "waiting": "waiting", "markBg": "mark-bg",
             "onAccent": "on-accent", "markInk": "mark-ink"}
    rgb = ",".join(str(int(c["canvas"][i:i + 2], 16)) for i in (1, 3, 5))
    qr_dark, qr_light = brand.qr_colors(c)
    tokens = "\n".join(f"  --{v}: {c[k]};" for k, v in names.items()) + f"\n  --qr-dark: {qr_dark};\n  --qr-light: {qr_light};"
    return (f"/* {b['label']}, theme {b['theme']}: written by tools/compose_scaffold.py from brands/{b['name']}/brand.json */\n"
            f"{font_faces('fonts')}\n:root {{\n{tokens}\n  --canvas-0: rgba({rgb},0);\n  --canvas-90: rgba({rgb},.9);\n}}\n")


def scaffold(source, pack=None, out=None, theme="default"):
    """A buildable HyperFrames project for one pack: the agent's pack-neutral source (index.html, compositions/s*.html,
    beats.json) copied into `out` (default out/compose/<story>-<pack>[-<theme>]/) with everything code owns written
    beside it, in the pack's default theme or `theme` (brand.json themes)."""
    source = pathlib.Path(source).resolve()
    sheet = json.loads((source / "beats.json").read_text(encoding="utf-8"))
    story = json.loads((ROOT / sheet["story"]).read_text(encoding="utf-8"))
    if pack:
        story["brand"] = pack
    b = brand.of(story, theme)
    suffix = "" if b["theme"] == b["default_theme"] else f"-{b['theme']}"
    project = pathlib.Path(out or ROOT / "out" / "compose" / f"{story['id']}-{b['name']}{suffix}").resolve()
    shutil.rmtree(project, ignore_errors=True)
    (project / "compositions").mkdir(parents=True)
    for f in ["index.html", "beats.json", *(f"compositions/{x.name}" for x in (source / "compositions").glob("*.html"))]:
        shutil.copy(source / f, project / f)
    story_path = project / "story.json"  # the story with the pack it is built for (props.build reads the pack there)
    story_path.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")
    t, p, work = timing(project, story_path, sheet, b["theme"])
    (project / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    (project / "assets" / "brand.css").write_text(brand_css(b), encoding="utf-8")
    (project / "assets" / "icons").mkdir(parents=True, exist_ok=True)
    (project / "compositions").mkdir(exist_ok=True)
    for w, f in b["_fonts"].items():
        shutil.copy(f, project / "assets" / "fonts" / f"brand-{w}.woff2")
    # GSAP from the pinned HyperFrames package, not the CDN: the compiler keeps an https script src as it is, so a
    # CDN reference would be fetched at every render
    (project / "assets" / "vendor").mkdir(exist_ok=True)
    shutil.copy(GSAP, project / "assets" / "vendor" / "gsap.min.js")
    for name in sheet.get("icons", []):
        (project / "assets" / "icons" / f"{name}.svg").write_text(icon_svg(name, b["colors"]["ink"]), encoding="utf-8")
    qr = meta.qr_svg(meta.links(story, "shorts", b)[1], *brand.qr_colors(b["colors"]))  # inline SVG: an <img> needs the xmlns
    (project / "assets" / "qr.svg").write_text(qr.replace("<svg ", "<svg xmlns=\"http://www.w3.org/2000/svg\" ", 1),
                                              encoding="utf-8")
    where = next((s for s in p["scenes"] if s.get("map")), None)
    if where:  # the country and the place, the same geometry at two scales (a scene crossfades them as it zooms)
        m = where["map"]
        country, focus = map_box(m["start"]), map_box(m["focus"])
        (project / "assets" / "map-country.svg").write_text(map_svg(m, country, b["colors"], 0), encoding="utf-8")
        (project / "assets" / "map-place.svg").write_text(map_svg(m, focus, b["colors"], 1), encoding="utf-8")
        t["map"].update({"box": [MAP_W, MAP_H], "country": country, "place": focus,
                         "pinsInCountry": [[round((x - country[0]) / country[2] * MAP_W, 1),
                                            round((y - country[1]) / country[3] * MAP_H, 1)] for x, y in m["pins"]],
                         "pinsInPlace": [[round((x - focus[0]) / focus[2] * MAP_W, 1),
                                          round((y - focus[1]) / focus[3] * MAP_H, 1)] for x, y in m["pins"]],
                         "placeInCountry": [round((focus[0] - country[0]) / country[2] * MAP_W, 1),
                                            round((focus[1] - country[1]) / country[3] * MAP_H, 1),
                                            round(focus[2] / country[2] * MAP_W, 1),
                                            round(focus[3] / country[3] * MAP_H, 1)]})
    # the story's pictures (tt_shorts/assets.py): the same ledger files Lane A draws, copied in, with their label and
    # credit; a composed scene may use only these (frame.md: no media without its licence in the ledger)
    drawn = assets.for_props(story, b, project / "assets", FPS)
    (project / "assets" / "media.json").write_text(json.dumps({
        "pictures": {k: {**v, "src": f"assets/{v['src']}"} for k, v in drawn.items()},
        "scenes": {i: s["media"]["asset"] for i, s in enumerate(story.get("scenes") or []) if s.get("media")},
        "ledger": story.get("assets") or []}, ensure_ascii=False, indent=1), encoding="utf-8")
    (project / "frame.md").write_text(frame_md.render(b), encoding="utf-8")
    (project / "timing.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    (project / "compositions" / "chrome.html").write_text(chrome(t, b, project), encoding="utf-8")
    (project / "compositions" / "captions.html").write_text(captions_html(p["captions"], t, b), encoding="utf-8")
    return project, t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="the agent's composition: index.html, compositions/s*.html, beats.json (compose/24835)")
    ap.add_argument("--brand", help="the pack to build for (default: the story's)")
    ap.add_argument("--theme", default="default", help="the pack's theme (default: its default_theme)")
    ap.add_argument("--out", help="the project folder to write (default out/compose/<story>-<pack>[-<theme>])")
    a = ap.parse_args()
    project, t = scaffold(a.source, a.brand, a.out, a.theme)
    print(json.dumps({"project": str(project), "duration": t["duration"], "chapters": t["chapters"], "gaps": t["gaps"],
                      "beats": [(x["id"], x["t"]) for x in t["beats"]]}, ensure_ascii=False))
