# Living Screencast (`living-screencast`)

> Software walkthrough where application windows and cursor navigation come alive with camera zooms, ripple clicks, and keyboard strokes.

## 1. At-a-Glance Signature
- Real application window or browser viewport on a pristine neutral desktop background.
- Animated vector cursor moving along natural bézier curves with speed easing between UI targets.
- Expanding circular ripple effect highlighting mouse clicks.
- Dynamic camera zooming punched directly into the active UI field or input box.

## 2. Screenshot & Domain Integrity Rules
- In accordance with Veasy brand law, screenshots are permitted **only from official verified domains** (`matsne.gov.ge`, `gov.ge` and subdomains) or the client's own domain (`sitech.ge`).
- No unauthorized external website scraping or uncredited publisher captures.

## 3. Vertical (1080×1920) Geometry & Safe Zones
- Vertical desktop frame: window is scaled to fit $x \in [72, 1008]$, $y \in [260, 1340]$.
- Window title bar: $y \approx 280$ with macOS/Linux style window controls and URL pill.
- Safe zone: interactive field and cursor action stay within $y \le 1380$; captions occupy $y \in [1380, 1552]$.
- Right margin clear zone: $x \le 940$ below $y = 1100$.

## 4. Georgian Mkhedruli Typography
- UI labels and form inputs rendered in authentic native fonts (`FiraGO` or system sans-serif).
- Active typing animation: characters appear one by one with a blinking vertical cursor pipe.
- URL bar displays clean domain and path.

## 5. Motion & Animation Rules
- Cursor moves along cubic bézier curves ($0.4–0.8\text{ s}$) with acceleration out and deceleration into clicks.
- Zoom punch: camera punches into target field ($1.0 \to 1.5$ scale) over 12 frames on click.
- Ripple click: circle expands ($12 \to 48\text{ px}$) and fades out over 10 frames.

## 6. Sound Craft
- Pleasant ambient tech pulse loop.
- Mix stays at constant volume without ducking.
- SFX: crisp mouse click (`click`), mechanical keyboard strokes (`tick`), and camera zoom whoosh (`whoosh`).
