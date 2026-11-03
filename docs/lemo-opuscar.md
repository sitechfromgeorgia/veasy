# Lemo-Opuscar and Veasy: what to take, what to leave, how to make Veasy simpler

Written 2026-11-03 from a read of [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) (MIT code and
docs; demo films and stills CC BY 4.0; 11.6k stars; last push 2026-10-31). The prompts that carry this plan out are
GOAL 6 and GOAL 7 in [antigravity-goals.md](antigravity-goals.md).

## 1. What it is

A **library of 66 film styles** for a coding agent (Claude Code), plus the method and tools to make a film in any of
them. There's no video model: every frame, note and cut is code.

- **A style** is `styles/<slug>/`, made of:
  - `STYLE.md`, about 12 fixed sections: essence and what it is not, materials and rendering, colour logic, type,
    motion, camera grammar, sound palette, native moves, pitfalls, engine, variation space;
  - `style.json`, the catalogue entry: name, category, uses;
  - a demo film made in code (`demo/`, `DEMO.md`) and a poster frame.

  The style is fixed. The story is always the user's.
- **The method**, three guides:
  - `AGENTS.md`: ask once, then no more questions; write the treatment before opening the demo.
  - `DIRECTOR.md`:
    - a benchmark first;
    - one subject, one goal, one turn;
    - a hook in the first 3 s;
    - one native move at the peak;
    - three candidate structures in `TREATMENT.md`, plus a shot list, a beat sheet, a cue map and a sound design table;
    - pacing for the reader;
    - at least four camera moves;
    - one fix round;
    - "not the demo again": at least 4 of 6 things must differ from the demo.
  - `TECHNIQUE.md`: one timeline drives picture, voice, music, sound and subtitles.
- **The tools** (`core/`):
  - **Rendering.** Any web page with `window.render(t)` is rendered frame by frame in headless Chrome (canvas 2D,
    WebGL or three.js), with parallel workers.
  - **readcheck.** The page reports every text on screen (`window.TEXTS(t)`), and a script checks that each one
    stays long enough to read.
  - **Voice.** TTS (Kokoro offline, or edge-tts), then a speech-to-text check of every line, comparing numbers by
    their value.
  - **Music.** A sampler that plays real instruments from free libraries (VSCO 2 CE, VCSL, Salamander, FreePats,
    Karoryfer), plus Karplus-Strong plucked strings for folk instruments.
  - **Sound and mastering.** Procedural foley, then a two-pass loudnorm mux.
  - **Review.** Contact sheets and `.srt` files.
- **"Make a style your own"** (`MY-STYLES.md`):
  - an interview, one question at a time, sorting the changes into safe to change, changes the character, and
    can't change;
  - then a style frame side by side with the base, a 15-30 s demo, and the style saved to `~/lemo-my-styles/`.
- **Distribution.** It installs as a Claude Code plugin from its own marketplace. The skill only fetches the library
  and hands over to `AGENTS.md`. A GitHub Pages gallery shows every style's film.

One film takes an agent 30-60 minutes. Every film is hand-directed, and a person asks for it and watches it.

## 2. Where Veasy already stands

| Lemo-Opuscar | Veasy today |
|---|---|
| 66 styles as prompts with reference code | 3 looks, 2 themes, 8 directors, rubrics, a variety rotation and a novelty guard: richer automation, much less visual range |
| An agent writes every film by hand | Two lanes: the Remotion kit (code-owned layout, the writer fills text) and the HyperFrames composed lane |
| `render(t)` canvas/WebGL page, any look | Remotion components and HyperFrames HTML/GSAP; no canvas/WebGL/3D path |
| readcheck (`TEXTS(t)`, chars ÷ 15 + 1.5 s) | motion_rules (0.5 s + 0.3 s a word) on `data-probe` regions, plus the layout probe and the contrast rule |
| ASR check with numbers by value | `align.py` plus `speech.voice_qa()`: Georgian wav2vec2 compares heard and given words; numbers are not compared by value |
| Sampler and plucked strings, a score per film | `compose_music.py`: synthesized loops per family, one constant level (the owner: no ducking) |
| Procedural foley tied to events | `sfx.py`: cues from the timeline, off by default |
| Contact sheet, storyboard on request | `engine plan` builds a contact sheet before any voice is paid for |
| FACTS.md for films that state facts | `news_check`, `claims_check`, programs' rule tiers: stricter, and enforced by code |
| Make a style your own | plan-v2 § 10 "any brand book in" (goal 5 is building `brand new --from`) |
| Claude Code plugin with a marketplace, a gallery page | Hermes plugin only; no gallery |
| Ask once, then no more questions | No single front door: brand, program, format, director, look, theme, engine, rubric, template |

Veasy is ahead on what Lemo-Opuscar doesn't try to do:
- publishing without a person;
- news rules;
- brand law;
- Georgian;
- variety across 1000 videos;
- costs.

Lemo-Opuscar is ahead on:
- visual range (66 looks, 3D, painting, print, cartoon);
- the directing method;
- sound craft;
- being simple to ask for.

## 3. What to take, ranked

1. **Styles as data** (`styles/<slug>/STYLE.md` + `style.json` + a demo story + stills).
   - A style is the one thing a user names ("make it in the Pictogram style").
   - Under it, code picks the engine, look, director, motion and sound. The writer still fills only text.
   - **Fit with the brand law:** a style declares `palette: pack` (it draws in the pack's palette and font, so it is
     allowed anywhere) or `palette: own` (it brings its own palette or fonts). An `own` style is allowed only where
     the pack lists it in a new `styles` key and the program allows it. News never uses one.
   - The pack stays law, because the pack opts in.
2. **Vertical, Georgian versions of the styles that fit.**
   - Every Lemo-Opuscar style is 1920×1080 and Latin/CJK, so each must be re-thought for 1080×1920, the safe zone
     and Mkhedruli.
   - First wave, brand-safe for news: Swiss Motion, Pictogram Motion, Caption News, Data Storytelling, Transit Map,
     Satellite Briefing (with Veasy's Georgia map rules, not theirs), Engineering Briefing Board, Whiteboard
     Explainer, Blueprint, Isometric Infographic, Countdown.
   - Second wave, for explainers, SiTech and stories: Dark Keynote, Living Screencast, Hologram HUD, Circuit Board,
     Crayon Book, One-line, Risograph, Halftone Dossier, Silkscreen Poster, Mid-century Toon, Paper Pop-up.
   - Then **Georgian styles of our own**, as they have their East Asian Traditions:
     - a naive painting style in the spirit of Pirosmani (public domain);
     - Tbilisi Soviet-modernist mosaic;
     - stone-carved Asomtavruli inscriptions;
     - Georgian ornament.
3. **A canvas/WebGL page inside the composed lane.**
   - Their `render(t)` page contract is what makes 3D, brushes and print looks possible.
   - Spike first: can a HyperFrames composition drive a canvas `render(t)` deterministically? If it can, styles run
     in Lane B and Veasy keeps two engines.
   - If it can't, write it up for the owner. A third engine is the owner's call, not an agent's.
4. **readcheck's contract, `TEXTS(t)`, for composed films.**
   - Every text on screen at a time, with its box.
   - One check covers both lanes, with Veasy's rule (0.5 s + 0.3 s a word) and the safe zone.
5. **Numbers checked by value in the voice.**
   - `speech.voice_qa()` learns Georgian numerals: ცხრამეტი = 19, ორი ათას ოცდაექვსი = 2026, პროცენტი.
   - A number heard as a different number fails the video.
   - This matters more for Veasy than for them: nobody watches before it publishes.
6. **Sound craft without breaking the owner's rules.**
   - Take the sampler (CC0 and CC BY libraries), so loops can have real instruments.
   - Take plucked-string modelling for Georgian folk timbres (panduri, chonguri) in our own style.
   - Take "every visible action has a sound" as an sfx option.
   - Keep one constant level: no ducking, no risers. Their advice to duck is the opposite of the owner's decision.
7. **The directing method, as Veasy's skills and plan checks.**
   - Already built in: hook in 3 s, one turn, one native move per style, at least 2 camera moves, and "not the
     template again" (the novelty guard does this).
   - The composed lane's skill asks for a short treatment (three structures, then a choice) before writing HTML.
8. **"Make a style your own" as an agent's interview**, next to `brand new --from`: safe / character / can't change,
   a style frame next to the base, a short demo, then saved under `brands/<name>/styles/` for that pack.
9. **A gallery**: one page of every style, look, scene and director, with a still and a 5 s clip from the probe,
   built by a command. It serves the owner, clients and agents choosing.
10. **Distribution to any AI.**
    - A Claude Code plugin manifest next to `plugin.yaml`, so Claude Code (and Antigravity, which reads skills
      folders) can install Veasy.
    - With goal 5's MCP proposal, any AI client could drive Veasy, not only Hermes.

## 4. What not to take

- Their map rules (China's view). Veasy has its own: Georgia's 12 regions, Abkhazia and Tskhinvali inside Georgia.
- Music ducking and build-ups: the owner rejected them.
- Kokoro: it has no Georgian. Gemini TTS stays; edge-tts stays a preview stand-in.
- Hand-directing every film as the default. Veasy publishes on its own; styles have to work through code-owned
  layout and checks.
- Their demo films, stills and three excluded voice tracks: CC BY with credit at best; we draw our own.
- 1920×1080 at 24 fps defaults: Veasy is vertical, at its own rate.
- Any style built on real footage or publisher photos (Visual Investigation, Archive Light Table, Newsreel), unless
  the material's licence allows it (`assets.LICENCES`, N13).

## 5. Simpler: one front door, three words

Today a person or an agent meets brand, program, format, director, look, theme, engine, rubric, template, captions,
music and sfx. Lemo-Opuscar's lesson is that a person needs three:

> **brand** (who it's for) · **style** (how it looks and sounds) · **story** (what it's about)

- **One request:** `veasy make "<what you want>" [--brand x] [--style y]`, or the `veasy:make-video` skill. It asks
  once, only what code can't decide (facts it can't find, materials, a storyboard or not), then runs to the end.
- **Code decides everything else.**
  - The program comes from the source.
  - The format comes from the program.
  - The director, look, theme, motion and music come from the style, through variety.
  - The engine comes from the style.
  - Without `--style`, variety picks one of the styles the brand allows, the least used lately.
- **Nothing is removed underneath.** Directors, looks and formats stay as the style's parts, and every expert flag
  still works. The front door just stops asking for them.
- **One catalogue.** `engine options` leads with brands and styles (with stills); everything else moves under
  "advanced".
- **Fewer skills to read first.** `veasy:make-video` is the only skill an agent needs to start; the others are
  references it follows when a step needs them.

Do this after goals 1-5 are merged, because it gathers what they add (GOAL 7).

## 6. Owner decisions

1. **`palette: own` styles:** which packs may use them (SiTech and other clients yes, tbilisi.today news no is the
   proposal), and for which programs.
2. **A canvas/WebGL path:** inside HyperFrames if the spike works; a third engine only on the owner's word.
3. **Georgian styles:** which ones to make first.
4. **The front door:** whether `style` becomes the word users and agents use, with directors and looks under it.
5. **Distribution:** a Claude Code plugin and an MCP server, beside Hermes.
