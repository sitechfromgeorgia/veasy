# Veasy Lit Surfaces — Results Report

## 1. Executive Summary

This report documents the design, implementation, and verification of **Veasy Lit Surfaces** (`plates/surface/`, `tools/build_surfaces.py`, `assets/surfaces/`).

Veasy frames previously had dark, empty space between $y = 600$ and $y = 1380$. Flat 2D textures cannot be dynamically lit because they lack surface normal information; moving light requires accurate tangent-space surface normals and microfacet reflectance. Furthermore, Veasy operates under strict constraints:
- Zero paid API calls at render time;
- Strict compliance with Georgian news and brand rules (monochrome tone only, no color leakage into client brand packs, strict safe zones);
- Fully deterministic output;
- Headless execution on CPU software GL (SwiftShader) within a strict time budget ($\le 83\text{ s}$ per 6-second plate bake);
- Clean repository footprint ($\le 15\text{ MB}$ total git budget for all surface assets).

---

## 2. Done When Scorecard & Evidence

| # | Done When Requirement | Status | Evidence |
|---|---|---|---|
| **1** | At least 4 materials shipped with ledger, however quota went, count stated | In Progress | Initializing materials pipeline and ledger |
| **2** | 12 loops baked behind real facts layouts, $\le 83\text{ s}$ per bake, loop closes without jump | In Progress | Mathematical loop formulation verified in `docs/research/lit-surfaces.md` |
| **3** | Text panels stay readable on every loop (critic judged), no banding on darkest loop | In Progress | TPDF blue noise anti-banding shader architecture specified |
| **4** | No generated image holds text, face, logo, or real place (critic inspected every one) | In Progress | Subagent critic verification protocol established |

---

## 3. Commit List

1. *Pending commit 1:* `docs(research): lit surfaces research, architecture, and ranked backlog`
   - Researched 24 real sources across 6 domains (museum raking light, normal derivation, seamless tiling, shader BRDF, mobile readability, dark banding).
   - Authored the one-line contract for users and agents.
   - Compiled license compliance table and ranked backlog.

---

## 4. Materials Ledger Summary

*To be populated as materials are baked and ledgered in `assets/surfaces/LEDGER.json`.*

---

## 5. Verification & Visual Evidence

*To be populated with still paths and probe results.*

---

## 6. Touched Shared Files

- None. Strictly confined to owned lane: `plates/surface/`, `tools/build_surfaces.py`, `assets/surfaces/`, `docs/research/lit-surfaces.md`, `docs/research/lit-surfaces-result.md`.

---

## 7. Proposed Addition to CLAUDE.md

```markdown
- **Lit Surfaces (`plates/surface/`, `tools/build_surfaces.py`, `assets/surfaces/`)**: Physical material relief plates relit by moving raking light (`rake`, `sweep`, `dawn`) for factual underlays. Strict tone only (monochrome), zero text/accent/logos. Built via `tools/build_surfaces.py` from verified AI-generated seamless height/normal maps with provenance in `assets/surfaces/LEDGER.json`. Never used for news, crime, incidents, or deaths.
```

---

## 8. Owner Decisions

- None pending at this stage. All requirements are within authorized boundaries.
