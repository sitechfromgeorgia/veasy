#!/usr/bin/env python3
"""Write one 6 s loop spec per procedural material into plates/surface/specs/ (loop_13..). Deterministic."""
import json
from pathlib import Path

from tools import surface_procedural as sp

LIGHTS = ["rake", "sweep", "dawn"]


def main() -> int:
    out = Path("plates/surface/specs")
    out.mkdir(parents=True, exist_ok=True)
    for i, mid in enumerate(sorted(sp.MATERIALS)):
        spec = sp.MATERIALS[mid]
        light = LIGHTS[i % 3]
        body = {"material": mid, "light": light, "scale": 1.0, "depth": spec["depth"],
                "roughness": spec["roughness"], "intensity": 1.0}
        (out / f"loop_{13 + i:02d}_{mid}_{light}.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
