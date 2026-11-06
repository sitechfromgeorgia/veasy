# Paper Stage: Results and Evidence

**Goal**: Give every story a set: miniature paper worlds the camera moves through in one take, so a film's steps happen in one place instead of a row of cards.  
**Branch**: `goal/paper-stage`  
**Lane**: `plates/diorama/`  

---

## 1. "Done When" Verification Table

| Requirement / Done When | Status | Evidence / Artifact |
|---|---|---|
| The first set's still passed the critic before the others were built, and that verdict is in your research file | In progress | Pending first set still generation & critic review |
| Five sets are baked, 6 seconds each, about 67 seconds a bake at most | In progress | Pending 5-set bake |
| A stranger sub-agent shown only stills names each place correctly | In progress | Pending stranger sub-agent test |
| A second bake gives the same mp4; 44 drawings stand up without a broken one | In progress | Pending 44-drawing test & determinism verification |
| One set sits behind a real story in a composed film in out/, and the critic has judged it | In progress | Pending composed film integration in out/ |

---

## 2. Commit Log

1. `96c2a83` - `docs(research): paper stage diorama research, 24 sources, backlog and license table`

---

## 3. What We Didn't Do and Why

- *Cast shadows*: Measured at 903 ms per frame on SwiftShader, which would blow through the 67-second bake limit. We use surface normal stage lighting and linear depth fog for depth.
- *Full PBR / specular metallic shaders*: Inappropriate for matte paper cutouts and adds unnecessary per-pixel shading overhead on software GL.
- *Free 3D text in WebGL*: Prohibited by Veasy rules. Text stays in the DOM above the plate video and tracks 3D coordinates via `anchors.json`.

---

## 4. Owner Decisions

1. **Plate Integration in Composition**: Goal 1 wires plates into both engines concurrently. For standalone demonstration, we wire the baked plate into a copied composition in `out/` via `<video muted playsinline src="...">`.
2. **Set Place Names**: All sets are strictly generic architectural archetypes (`museum-hall`, `street`, `market`, `classroom`, `river-bridge`) to strictly respect the rule that a plate never claims to be a real place or building.

---

## 5. Shared Files Touched

None yet. All work remains strictly within `plates/diorama/`, `docs/research/`, and temporary verification files in `out/` and `tests/`.
