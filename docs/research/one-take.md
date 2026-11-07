# one-take: research (ROADMAP D5)

One line for the user: `"transition": "one-take"` in a format (or nothing: variety picks it for a program film).
What they get back: scenes that sit on one 2D path, a camera that glides between them only during the cuts, and the
accent dot running the thread to the next scene. `news` never gets it.

## What the build needs (and where it comes from)

| Source | What it gives the build |
|---|---|
| Heer and Robertson, animated transitions in statistical graphics (cited in `reports/Veasy უნიკალური ვიდეოების გაძლიერება.md`) | Congruent, staged motion keeps the viewer's mental map: one clear move between states beats a dissolve. So the camera moves along one axis-aligned-ish line per cut, never reverses straight back. |
| Poynter, "The meaning of motion: Ken Burns" (same report) | Motion needs a reason: reveal, connect, or stop. Our reason is "connect": the thread and the dot say where the story goes next. No camera drift while text is read. |
| Remotion docs, `@remotion/paths` (`getLength`, `getPointAtLength`, `evolvePath`), https://www.remotion.dev/docs/paths | MIT; pure functions of a path string, so the dot's place is a pure function of the frame. Pin to the other Remotion packages (4.0.539). Checked: the package ships types, no side effects. |
| Remotion `interpolate`/`Easing` | Frame-pure easing; no `Math.random`, no clock. |
| Parallax in 2D (multiplane camera idea; background layers move at a fraction of the foreground) | Depth with no 3D: layers at 0.2, 0.4 and 0.65 of the camera's move, near layers drawn larger. All behind the scenes. |
| Camera grammar of one-take sequences (the paper-stage goal's notes, `docs/antigravity-goals-2.md` goal 4) | A move reads as one take when the thread is continuous: the camera's exit direction is the next move's entry direction (turn at most 90 degrees). |
| ITU-R BT.1702 (already in `tt_shorts/flash.py`) | A pan over faint tiles must not flash: layers are the pack's faint grid colour at low contrast, and `flash.qa_file` still judges the render. |

## Design decisions taken from that

1. **The camera moves only in a cut window** of `CUT` = 12 frames (0.4 s) that starts at the new scene's first frame.
   The old scene stays alive for those 12 frames after its end (no fade: the camera carries it away). At rest the
   transform is the identity, so text never moves while read and the layout probe (settled frame = scene start + 12)
   sees exactly what a plain cut shows.
2. **Zoom**: a bell over the cut, `1 + z * sin(pi u)` with `|z|` seeded in 0.04..0.10, capped at `ZOOM_CAP` = 1.15;
   exactly 1 at rest. Negative z (pull back) is allowed.
3. **Path** (`tt_shorts/onetake.py`, pure): scene i sits at `P_i`; the step is one of eight compass directions, sized to
   the viewport plus a gutter, chosen from the seed (crc32 of the story id), the arriving scene's shape (lists and
   steps move down, maps and numbers move sideways, the end card arrives from the side it can't be confused with) and
   a no-reversal rule. Two films get two routes; one story always gets its route again.
4. **Chrome fixed**: header, ticker, captions and footer are not inside the camera. Only the scene band (clipped to
   SCENE_TOP..SCENE_BOTTOM) rides it.
5. **Thread and dot**: a cubic bezier from the old scene's anchor to the new one's, drawn in ink while the cut runs, the
   accent dot leading it (`getPointAtLength`); gone at rest. The accent is only the dot.
6. **Not for news**: the option is offered only to a story with a `program` other than `news`; an explicit request on a
   story with no program is refused with a message. Whether news should get it (ROADMAP imagines it with the zoom cap)
   is the owner's call.

## Not researched (said plainly)

No web search was made in this run beyond the Remotion paths docs summary above (not re-fetched: written from the
package's published API); the licences of the other sources are not used as code, only as ideas. The routes' look is
judged by the critic's contact sheet, not by a source.
