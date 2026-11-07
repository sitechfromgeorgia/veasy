// How a number reads on screen. A fact keeps every digit it came with: a count-up ends on the exact value, never on a
// rounded one. Pure, so tests/test_numbers.py can run it without a browser.

export const decimalsOf = (n: number) => (String(n).split(".")[1] ?? "").length;

/** The value a count-up shows at progress t (0 to 1): whole steps for a whole number, the fact's own decimals otherwise. */
export const counted = (to: number, t: number) => {
  if (t >= 1) return to;
  const d = decimalsOf(to);
  return d ? Number((to * t).toFixed(d)) : Math.round(to * t);
};

/** Georgian writing (ka_style.md): a space between thousands, a comma before the decimals ("6 400", "3,8"). */
export const group = (n: number, decimals = decimalsOf(n)) =>
  n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    .replace(/,/g, " ").replace(".", ",");
