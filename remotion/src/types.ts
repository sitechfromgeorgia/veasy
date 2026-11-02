// Render props: built by tt_shorts/props.py from a story JSON (the writer's text) plus the data (date, sources, QR),
// the brand pack and the voice's word timings. The composition never invents text.

// editorial: calm, grid, rising type · kinetic: giant type, hard cuts, inverted blocks · cards: site-style story cards
export type Variant = "editorial" | "kinetic" | "cards";

export type Word = { text: string; start: number; end: number }; // seconds

// tt_shorts/captions.py: the caption layout, computed once per video with the real font (seconds)
export type CaptionWord = { text: string; from: number; to: number };
export type CaptionLayout = {
  design: "page" | "roll";
  size: number;
  lineHeight: number;
  band: number;
  pad: number;
  lines: { start: number; words: CaptionWord[] }[];
  pages: { start: number; end: number; lines: number[] }[];
};

// who {name, role} · pair {title, sub} · bars and trend {label, value} · points and steps: plain strings
export type Item = string | { name?: string; role?: string; title?: string; sub?: string; label?: string; value?: number };

// tt_shorts/art.py: one SVG element; colors are brand tokens, motion r (rise) | p (pop) | s (stroke draws itself)
export type ArtNode = {
  tag: string;
  attrs: Record<string, string>;
  motion: "r" | "p" | "s" | null;
  delay: number; // seconds into the scene
  children: ArtNode[];
  text: string | null;
};

// the cut between scenes (tt_shorts/props.py TRANSITIONS); "auto" is resolved in Python
export type Transition = "cut" | "line" | "panel" | "wipe" | "slide" | "push" | "dot";

// the ending (tt_shorts/swipe.py OUTROS): the end card, a QR/link/CTA chip over the last scene, or a seamless loop
export type Outro = "card" | "overlay" | "loop";

// tt_shorts/variety.py: this video's own combination inside the brand and the look (layout and motion, never color)
export type Style = {
  hook: "stack" | "lead" | "blocks" | "underline";
  motif: "grid" | "diagonal" | "dots" | "rules" | "plain";
  enter: "rise" | "slide" | "reveal" | "scale";
};

export type SceneBase = { type: string; from: number; duration: number; kicker?: string; headline?: string };

export type Scene = SceneBase & {
  lines?: string[];
  value?: number;
  prefix?: string;
  suffix?: string;
  label?: string;
  big?: string;
  start?: string;
  end?: string;
  place?: string;
  sub?: string;
  items?: Item[];
  art?: ArtNode[]; // draw: the drawing, sanitized by tt_shorts/art.py
  between?: string; // pair: the word on the divider
  unit?: string; // bars, trend, change
  before?: { label: string; value: number }; // change
  after?: { label: string; value: number };
  text?: string;
  by?: string;
  via?: string;
};

// tt_shorts/brand.py for_remotion(): the brand pack, without file paths
export type BrandProps = {
  name: string;
  label: string; // "tbilisi.today", "SiTech": the ticker's name
  colors: {
    canvas: string; panel: string; ink: string; muted: string; accent: string; onAccent?: string; line: string;
    lineStrong: string; grid: string; ticker: string; waiting: string; markBg: string;
  };
  wordmark: { text: string; accent?: string }; // the accent character is drawn in the accent color
  logo: "tmark" | "svg"; // svg: public/brand/header.svg and end.svg
  footer: { text: string; strong?: string };
  strings: {
    outlets: string; source_one: string; source_many: string; covered_by: string[]; today: string;
    preview_edge: string; preview_silent: string; card_meta: string; category_default: string;
  };
};

export type ShortProps = {
  brand: BrandProps;
  variant: Variant;
  transition: Transition;
  style?: Style; // absent: the look's own (stack; grid or diagonal; rise or slide)
  outro?: Outro; // absent: the end card
  outroFrom?: number | null; // overlay and loop: the frame the chip comes in
  id: number;
  category: string; // Georgian label
  date: { date: string; time: string; weekday: string };
  when: string; // "დღეს" or the date
  sources: string[];
  cta: string;
  url: string; // shown, from the pack's link.display: tbilisi.today/stories/<id>
  qrSvg: string; // segno SVG of the tracked story URL
  durationInFrames: number;
  scenes: Scene[];
  words: Word[];
  captions: CaptionLayout | null;
  voice: string | null; // file in the public dir
  voiceVolume: number;
  voiceTrim?: number; // seconds of leading silence cut from the voice (the word timings already moved)
  music: string | null;
  musicVolume: number;
  sourcesLine: string; // "წყარო: პირველი არხი, იმედი ნიუსი +5"
  previewNote: string | null; // e.g. the temporary preview voice, shown small above the ticker
};
