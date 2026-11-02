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
  items?: (string | { name: string; role?: string })[];
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
  music: string | null;
  musicVolume: number;
  sourcesLine: string; // "წყარო: პირველი არხი, იმედი ნიუსი +5"
  previewNote: string | null; // e.g. the temporary preview voice, shown small above the ticker
};
