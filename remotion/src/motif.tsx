import React from "react";
import { GRID } from "./brand";
import { IconTile } from "./icons";
import type { IconNode, Style } from "./types";

/** The size of one tile of a motif, px. */
export const motifCell = (motif: Style["motif"], tile: boolean) => tile ? 200 : motif === "dots" ? 48 : motif === "rules" ? 96
  : motif === "waves" ? 80 : motif === "crosses" ? 64 : motif === "mesh" ? 80 : motif === "hash" ? 56 : 72;

/** One tile of a motif (the pack's faint color by default): NewsShort's Background tiles it; the one-take camera's
 *  parallax layers (onetake.tsx) tile the same marks at other sizes. */
export const motifMark = (motif: Style["motif"], cell: number, tile: IconNode[] | null | undefined, color: string = GRID) => {
  return {
    grid: <path d={`M${cell} 0H0V${cell}`} fill="none" stroke={color} strokeWidth={2} />,
    diagonal: <path d={`M0 ${cell}L${cell} 0`} fill="none" stroke={color} strokeWidth={2} />,
    dots: <circle cx={cell / 2} cy={cell / 2} r={3} fill={color} />,
    rules: <path d={`M0 ${cell - 1}H${cell}`} fill="none" stroke={color} strokeWidth={2} />,
    plain: null,
    icons: tile ? <IconTile nodes={tile} cell={cell} color={color} /> : null,
    crosses: (
      <path
        d={`M${cell / 2 - 6} ${cell / 2}H${cell / 2 + 6} M${cell / 2} ${cell / 2 - 6}V${cell / 2 + 6}`}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
      />
    ),
    mesh: (
      <path
        d={`M0 ${cell / 2}L${cell / 2} 0L${cell} ${cell / 2}L${cell / 2} ${cell}Z`}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
      />
    ),
    waves: (
      <path
        d={`M0 ${cell / 2} Q${cell / 4} ${cell / 4} ${cell / 2} ${cell / 2} T${cell} ${cell / 2}`}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
      />
    ),
    hash: (
      <path
        d={`M${cell * 0.25} ${cell * 0.75}L${cell * 0.75} ${cell * 0.25} M${cell * 0.45} ${cell * 0.95}L${cell * 0.95} ${cell * 0.45}`}
        fill="none"
        stroke={color}
        strokeWidth={1.8}
        strokeLinecap="round"
      />
    ),
  }[motif];
};
