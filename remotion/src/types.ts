// Render props: built by video/tt_shorts/props.py from a story JSON (the writer's text) plus the data
// (date, sources, QR) and the voice's word timings. The composition never invents text.

// editorial: calm, grid, rising type · kinetic: giant type, hard cuts, inverted blocks · cards: site-style story cards
export type Variant = "editorial" | "kinetic" | "cards";

export type Word = { text: string; start: number; end: number }; // seconds

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

export type ShortProps = {
  variant: Variant;
  id: number;
  category: string; // Georgian label
  date: { date: string; time: string; weekday: string };
  when: string; // "დღეს" or the date
  sources: string[];
  cta: string;
  url: string; // shown: tbilisi.today/stories/<id>
  qrSvg: string; // segno SVG of the tracked story URL
  durationInFrames: number;
  scenes: Scene[];
  words: Word[];
  voice: string | null; // file in the public dir
  voiceVolume: number;
  music: string | null;
  musicVolume: number;
  sourcesLine: string; // "წყარო: პირველი არხი, იმედი ნიუსი +5"
  previewNote: string | null; // e.g. the temporary preview voice, shown small above the ticker
};
