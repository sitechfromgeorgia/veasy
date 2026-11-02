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

// who and link {name, role} · pair {title, sub} · bars, trend and compare {label, value} · rail {when, label} ·
// points and steps: plain strings
export type Item = string | {
  name?: string; role?: string; title?: string; sub?: string; label?: string; value?: number; when?: string;
  text?: string; count?: number; // agree: a fact and how many member articles state it (code counts them)
};

// tt_shorts/marks.py: a scene's voice-synced mark (its "em"), resolved in Python. field: the slot it sits in
// ("lines.2", "items.0.name", "value"...); start: where the phrase begins in that text; at: the scene frame the voice
// starts saying it; frames: how long the stroke takes. kind is code's (never the writer's); roughness 0 is a clean
// stroke (hard and service news), above 0 a little wobble (light news). Drawn in ink, never the accent.
export type MarkKind = "underline" | "box" | "circle" | "highlight" | "bracket";
export type MarkProps = {
  field: string; start: number; phrase: string; kind: MarkKind; at: number; frames: number; seed: number;
  roughness: number; bowing: number;
};

// stat: how the number arrives (tt_shorts: brushes/stat.json; flap never for politics or crime)
export type StatStyle = "count" | "wheel" | "flap";

// tt_shorts/art.py: one SVG element; colors are brand tokens, motion r (rise) | p (pop) | s (stroke draws itself)
export type ArtNode = {
  tag: string;
  attrs: Record<string, string>;
  motion: "r" | "p" | "s" | null;
  delay: number; // seconds into the scene
  children: ArtNode[];
  text: string | null;
};

// tt_shorts/icons.py: one Lucide icon's shapes on its 24 px grid, [tag, geometry attributes]; no colors
export type IconNode = [string, Record<string, string>];
// what a sign scene shows happening to its icon (icons.VERBS)
export type Verb = "rises" | "falls" | "stops" | "opens" | "closes" | "moves" | "splits" | "joins";

// the cut between scenes (tt_shorts/props.py TRANSITIONS); "auto" is resolved in Python
export type Transition = "cut" | "line" | "panel" | "wipe" | "slide" | "push" | "dot";

// the ending (tt_shorts/swipe.py OUTROS): the end card, a QR/link/CTA chip over the last scene, or a seamless loop
export type Outro = "card" | "overlay" | "loop";

// tt_shorts/variety.py: this video's own combination inside the brand and the look (layout and motion, never color)
export type Style = {
  hook: "stack" | "lead" | "blocks" | "underline";
  motif: "grid" | "diagonal" | "dots" | "rules" | "plain" | "icons"; // icons: props.motifIcon tiled
  enter: "rise" | "slide" | "reveal" | "scale";
  // tt_shorts/directors.py: the video's director, its motion personality and its current (absent: today's motion)
  director?: string;
  motion?: Motion;
  current?: "left" | "right" | "up";
  flow?: [number, number]; // the current's unit vector: slide entrances and directional cuts move along it
};

// a director's spring (mass 0.8), the frames a scene takes to come in, and the gap between items (5 = today's)
export type Motion = { damping: number; stiffness: number; enter_frames: number; stagger_frames: number };

// tt_shorts/geo.py: what a where scene draws of Georgia's map, in the map's viewBox units (projected in Python).
// start and focus are the camera's first and last view [x0, y0, x1, y1]; level says how close it goes (a district
// only outside the crime family).
export type GeoMap = {
  viewBox: number[];
  land: string; // the outline (SVG path)
  borders: string; // the lines between the regions
  rivers: string; // Mtkvari, Rioni, Alazani...: drawn inside the outline only
  regions: string[]; // the highlighted region(s)
  start: number[];
  focus: number[];
  pins: number[][];
  level: "country" | "region" | "district";
  credit: string; // the boundary data's licence credit, shown small
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
  area?: string; // where: ge, ge:<region> or ge:<place>, when the place text alone doesn't say it
  map?: GeoMap; // where: set by tt_shorts/geo.py when the place is in Georgia
  items?: Item[];
  art?: ArtNode[]; // draw: the drawing, sanitized by tt_shorts/art.py
  between?: string; // pair: the word on the divider
  unit?: string; // bars, trend, change
  before?: { label: string; value: number }; // change
  after?: { label: string; value: number };
  icon?: string; // sign, stat: the icon's library name (resolved in Python)
  verb?: Verb; // sign
  glyph?: IconNode[]; // sign, stat: the icon's shapes
  isotype?: boolean; // stat: the value is drawn as that many icons (2-30 whole things)
  text?: string;
  by?: string;
  via?: string;
  style?: StatStyle; // stat: count (default), wheel (an odometer) or flap (a split-flap board)
  edge?: string; // link: the verb on the edge, said in the scene's narration (N11)
  em?: string; // the writer's phrase; what is drawn is `mark`
  mark?: MarkProps; // set by tt_shorts/props.py (speech.mark_frames)
  n?: number; // agree: at least this many outlets state each fact · chapter: this story's number
  of?: number; // chapter: how many stories the digest has
  total?: number; // agree: the member articles code counted across
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
    at_least: string; // "მინიმუმ {n}": the agree scene's count
  };
};

export type ShortProps = {
  brand: BrandProps;
  variant: Variant;
  transition: Transition;
  style?: Style; // absent: the look's own (stack; grid or diagonal; rise or slide)
  outro?: Outro; // absent: the end card
  outroFrom?: number | null; // overlay and loop: the frame the chip comes in
  motifIcon?: IconNode[] | null; // the story's main icon, when the style's motif is "icons"
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
  rubric?: string | null; // tt_shorts/rubrics.py chip(): „დღის ციფრი · #12“, drawn in the hook (code's text)
  probe?: boolean; // tt_shorts/probe.py: report where every text block is (remotion/src/Probe.tsx)
};
