# The Edit Room: Incremental Scene Rendering, Plain-Word Steering, and Pre-Run Cost Inspection

## The One-Line User & Agent Interface

**What a person or agent types:**
```bash
python -m tt_shorts.engine steer demo/film-partia.json --scene 1 --set label="21 სექტემბრიდან 2 ნოემბრამდე" --dry
```

**What they get back (before running):**
```json
{"ok": true, "dry": true, "engine": "remotion", "scene": 1, "summary": "4.0 s of picture (scene 1 of 11, frames 116-235), $0.00", "cost": {"seconds": 4.0, "frames": 120, "total_frames": 2520, "dollars": 0.0, "voice": "cached", "full_render": false, "dirty_scenes": [1], "cached_scenes": [0, 2, 3, 4, 5, 6, 7, 8, 9, 10]}}
```

**And when run without `--dry`:**
Only Scene 1 (`120` frames out of `2,520`) redraws; the other 10 scenes come from the content-addressed segment cache (`$VEASY_HOME/cache/segments/`), FFmpeg stitches the video segments losslessly and mixes the continuous voice/music track once (`props.mix_audio`), and `<render>.room.html` updates beside the MP4 with every scene's still, words, timing, rhythm, pre-run cost table, and one-click copyable `steer` commands.

---

## 1. Research: 21 Authoritative Sources Across Five Domains

### Domain A: Incremental & Partial Rendering in Video Tools

1. **Remotion — Partial Frame-Range Rendering (`--frames` / `frameRange`)**
   - **Source:** [Remotion CLI `render --frames` Documentation](https://www.remotion.dev/docs/cli/render#--frames) & [`renderMedia()` `frameRange` API](https://www.remotion.dev/docs/renderer/render-media#framerange)
   - **What it teaches Veasy:** Remotion's `--frames=START-END` seeks Chromium directly to the inclusive global frame interval `[START, END]` on the root `NewsShort` composition while evaluating `useCurrentFrame()` at the true global frame index. In `remotion/src/NewsShort.tsx` (lines 433–439), every scene `i` is mounted inside `<Sequence key={i} from={s.from} durationInFrames={s.duration}>` with `s.from = marks[i]` and `s.duration = marks[i+1] - marks[i]`. Both incoming transitions (`<Cut />`, `enterFrames`) and outgoing transitions (`EXIT = 7` frames, `<MeterRise />`) live *inside* scene `i`'s own `<Sequence>`. Therefore, rendering `--frames={s.from}-{s.from + s.duration - 1}` produces pixels identical to a full render while preserving continuous global header progress, background drift, ticker scroll, and caption timing.

2. **HyperFrames — Time-Span Rendering (`--start` / `--end`) & Sub-Composition Addressing**
   - **Source:** [HeyGen HyperFrames CLI & Core Reference](https://github.com/heygen-com/hyperframes) (`compose/node_modules/hyperframes`, `renderSpan` / `spanFrameRange`)
   - **What it teaches Veasy:** `npx hyperframes render <project> --output <seg.mp4> --start <sec> --end <sec> --fps 30 --quality standard` converts `[start_sec, end_sec]` via `Math.round(sec * fps)` into half-open global frame indices `[startFrame, endFrame)` and encodes H.264 `yuv420p` with `lockGopForChunkConcat: true`, `closedGop: true`, and `forceKeyframes: "n=0"`. Rendering root time spans rather than isolated `-c compositions/s{i}.html` preserves locked `compositions/chrome.html` and `compositions/captions.html` at `z-index: 30`.

3. **Blackmagic DaVinci Resolve — Smart Render Cache & Segment Invalidation**
   - **Source:** [DaVinci Resolve 19 Reference Manual: Using the Render Cache (Smart vs. User Mode)](https://documents.blackmagicdesign.com/UserManuals/DaVinci_Resolve_19_Reference_Manual.pdf)
   - **What it teaches Veasy:** Resolve splits timeline playback into cached ("Blue") and dirty ("Red") clip spans, tracking transition overlap handles separately from clip bodies. In Veasy's HyperFrames lane (`tt_shorts/compose.py`), `host_spans(index_html)` may have a scene host with `data-until="end" data-until-shift="0.3"` that overlaps the next cut by `0.3s` (9 frames); hashing all scene hosts whose active interval overlaps `[start_sec, end_sec]` ensures any overlapping transition span turns dirty automatically when either contributing scene changes.

4. **Adobe After Effects — Persistent Disk Cache & Frame Hash Invalidation**
   - **Source:** [Adobe After Effects User Guide: Memory, Storage, and Persistent Disk Cache](https://helpx.adobe.com/after-effects/using/memory-storage1.html) & [AE Plugin SDK `PF_Cmd_USER_CHANGED_PARAM`](https://ae-plugins.docsforadobe.dev/)
   - **What it teaches Veasy:** After Effects indexes cached frames by a hash of active layer states, transforms, fonts, and effects, but suffers from stale "ghost frames" when untracked global state leaks into a layer. Veasy avoids ghost frames by prohibiting `Math.random()` / `Date.now()` and including every cross-scene dependency in each segment's hash: global `style`, `durationInFrames` (header progress bar), `chapters`, `motifIcon`, the time-window slice of `captions` overlapping `[t0, t1]`, and `scenes[0]` on the final segment when `outro == "loop"` (`<LoopBack />` in `remotion/src/outro.tsx`).

5. **Blender Video Sequence Editor (VSE) — `ID_RECALC_SEQUENCER_STRIPS` Dependency Graph**
   - **Source:** [Blender Manual: Video Editing Preview & Cache Settings](https://docs.blender.org/manual/en/latest/video_editing/preview/sidebar.html) & [Blender VSE Developer Docs](https://developer.blender.org/docs/features/vse/)
   - **What it teaches Veasy:** Blender separates **content-dirty** edits (a scene strip's internal text/layout changes while its start and duration stay fixed -> only 1 strip invalidates) from **duration-dirty** edits (changing a strip's duration -> shifts downstream timeline frames). Veasy's `--dry` cost model surfaces this distinction directly to the user before rendering.

---

### Domain B: How Non-Linear Editors Track Dirty State

6. **Pixar / ASWF OpenTimelineIO — `opentime.RationalTime` & `TimeRange`**
   - **Source:** [OpenTimelineIO Time Ranges Tutorial](https://opentimelineio.readthedocs.io/en/latest/tutorials/time-ranges.html) & [OTIO Timeline Structure](https://opentimelineio.readthedocs.io/en/latest/tutorials/otio-timeline-structure.html)
   - **What it teaches Veasy:** Floating-point second arithmetic (`2.333 + 1.667`) causes 1-frame rounding gaps or overlaps at 30 fps. Veasy's `tt_shorts/segments.py` computes all segment boundaries in exact integer frames at `FPS = 30` (`seg_start = s["from"]`, `seg_end = s["from"] + s["duration"] - 1`) and converts to `seg_start / 30.0` and `(seg_end + 1) / 30.0` only at the HyperFrames CLI boundary.

7. **Foundry Nuke — Node Graph `Op::append(Hash&)` & `NO_RERENDER` Knobs**
   - **Source:** [Foundry Nuke NDK Developer Guide: Hashing, Caching, and `Op::append(Hash&)`](https://learn.foundry.com/nuke/developers/15.0/ndkdevguide/2d/architecture.html)
   - **What it teaches Veasy:** Nuke operators hash only upstream inputs and knobs that affect pixel output, marking non-visual or post-render parameters with `NO_RERENDER`. In Veasy, both Remotion (`--muted`) and HyperFrames render silent video streams, while voice, music (`MUSIC_DB`), and SFX (`sfx.py`) are mixed afterward in `props.mix_audio()`. Excluding audio-only fields (`music`, `sfx`, `voiceTrim`, `novelty`, `voiceQa`) from the visual segment hash avoids unnecessary browser renders when only audio mix parameters change.

8. **Avid Media Composer & AMWA AAF — `CompositionMob` vs. `Precompute` Media**
   - **Source:** [AMWA Advanced Authoring Format (AAF) Object Specification v1.1](https://amwa.tv/projects/MS-01/)
   - **What it teaches Veasy:** Avid separates the timeline edit recipe (`CompositionMob`) from pre-rendered segment files (`Precompute` `SourceMob`). Veasy mirrors this by storing immutable rendered segments in `$VEASY_HOME/cache/segments/<sha16>/segment.mp4` (with `meta.json`) and writing a per-render `segments.json` manifest in the work directory that maps each scene slot `0..N-1` to its `sha16`.

9. **Apple Final Cut Pro — Magnetic Timeline Storyline Anchors & Render Range Bars**
   - **Source:** [Final Cut Pro User Guide: Manage Render Files and Background Rendering](https://support.apple.com/guide/final-cut-pro/manage-render-files-ver68a8c250/mac)
   - **What it teaches Veasy:** In Final Cut Pro's Magnetic Timeline, connected visual clips anchor to the primary audio storyline. In Veasy, the spoken narration (`words` from `speech.py`) is the primary storyline and each scene's `at` phrase is a magnetic anchor (`speech.anchor(words, phrase)`). As long as narration text does not change, word timestamps are locked (`speech.cache_key`) and editing scene `i`'s visual fields (`label`, `headline`, `kicker`, `value`, `sub`, `note`, `items`, `lines`) cannot move `marks[i+1]`.

---

### Domain C: Content-Addressed Caches & Early Cutoff

10. **Bazel — Remote Execution API v2 (Action Cache, CAS & Merkle Input Trees)**
    - **Source:** [Bazel Remote Caching Architecture](https://bazel.build/remote/caching) & [`remote_execution.proto`](https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto)
    - **What it teaches Veasy:** Bazel hashes an action's command line, environment, and a Merkle digest of all input files (`ActionKey`) to look up cached outputs in the Content-Addressable Store (CAS). `tt_shorts/segments.py` constructs a canonical JSON digest combining the engine identifier, template/code digest, scene index, frame span, scene payload, media file SHA-256, overlapping caption slice, and global chrome state.

11. **Nix — Input-Addressed vs. Content-Addressed Derivations (`ca-derivations` Early Cutoff)**
    - **Source:** [Nix Reference Manual: Store Paths & Content-Addressed Derivations](https://nix.dev/manual/nix/latest/store/store-path.html)
    - **What it teaches Veasy:** Early cutoff stops a build graph from cascading when an intermediate step produces identical output for unaffected downstream nodes. In Veasy, `speech.cache_key(story, voice)` provides early cutoff for TTS alignment, and slicing `props["captions"]["pages"]` to `[t0 - 0.25, t1 + 0.05]` provides early cutoff for caption rendering across unaffected scenes.

12. **Git — Content-Addressable Object Model (`blob`, `tree`, `commit`)**
    - **Source:** [Pro Git (2nd Ed.), §10.2 Git Internals — Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
    - **What it teaches Veasy:** A film render is a `tree` of ordered scene segment hashes `[sha_0, sha_1, ..., sha_{N-1}]`. Diffing a proposed edit (`steer --dry`) against the existing render is an $O(N)$ comparison of segment hashes: scenes with matching hashes are instant cache hits (`0` frames rendered), and reverting an edit later immediately reuses the earlier segment blobs still in `$VEASY_HOME/cache/segments/`.

13. **ccache — Direct Mode Manifests**
    - **Source:** [ccache Manual: How ccache works (Direct Mode vs. Preprocessor Mode)](https://ccache.dev/manual/latest.html#_how_ccache_works)
    - **What it teaches Veasy:** ccache avoids running the C preprocessor by hashing source files and included headers directly via a lightweight manifest. In `tt_shorts/segments.py`, hashing the Remotion source tree (`remotion/src/**/*.tsx`) or HyperFrames composition files (`compositions/*.html`, `styles/*.css`, `assets/*`) in Python takes `< 5 ms` without booting Node/Chromium for cache-hit scenes.

---

### Domain D: Frame-Accurate Concat, Splicing & Audio Mixing in FFmpeg

14. **FFmpeg Concat Demuxer (`-f concat`) vs. Concat Filter (`-filter_complex concat`)**
    - **Source:** [FFmpeg Wiki: Concatenate](https://trac.ffmpeg.org/wiki/Concatenate) & [FFmpeg Formats Documentation: `concat` demuxer](https://ffmpeg.org/ffmpeg-formats.html#concat-1)
    - **What it teaches Veasy:** The `concat` demuxer (`ffmpeg -y -f concat -safe 0 -i list.txt -map 0:v:0 -c:v copy -an`) joins H.264 segments in `< 0.15 s` with zero generation loss and 100% bit-identical frames, provided all segments share codec, resolution (`1080x1920`), pixel format (`yuv420p`), frame rate (`30/1`), and start with an IDR keyframe. If stream-copy verification ever detects a frame count mismatch or non-uniform stream parameters, `segments.py` automatically falls back to a clean `-c:v libx264 -pix_fmt yuv420p -r 30 -crf 18` encode of the join.

15. **ITU-T H.264 / x264 — Closed GOPs, IDR Keyframes & SPS/PPS Consistency**
    - **Source:** [ITU-T Rec. H.264 (§3.67 Instantaneous Decoding Refresh)](https://www.itu.int/rec/T-REC-H.264) & [x264 Settings Reference](https://www.chaneru.com/Roku/HLS/X264_Settings.htm)
    - **What it teaches Veasy:** Slicing an existing long-GOP MP4 at arbitrary scene boundaries with `-c copy` corrupts P/B frames when a cut does not land on an IDR frame. By rendering each scene segment `[seg_start, seg_end]` as its own range render (`--frames` in Remotion, `--start/--end` in HyperFrames), frame 0 of every segment is guaranteed to be an IDR keyframe with closed GOP boundaries.

16. **FFmpeg Container Timestamps — `PTS`, `DTS`, and `-fflags +genpts -avoid_negative_ts make_zero`**
    - **Source:** [FFmpeg Main Options Documentation: `-avoid_negative_ts` & `-fflags`](https://ffmpeg.org/ffmpeg.html#Main-options)
    - **What it teaches Veasy:** Passing `-fflags +genpts -avoid_negative_ts make_zero` during segment concatenation normalizes monotonic PTS/DTS tables across segment boundaries so `ffprobe` and downstream players see a continuous 30 fps stream with exact total frame count `durationInFrames`.

17. **EBU R 128 (`loudnorm`) & AAC 1024-Sample Framing — Why Voice Must Never Be Spliced by Sentence**
    - **Source:** [EBU Tech 3341 / R 128 Loudness Normalisation](https://tech.ebu.ch/publications/r128) & [FFmpeg `loudnorm` / `amix` Filter Documentation](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)
    - **What it teaches Veasy:** `props.mix_audio()` normalizes voice with `loudnorm=I=-16:TP=-2:LRA=7` (a program-wide EBU R 128 filter) and loops the music bed continuously at `-13 dB`. Furthermore, AAC encodes in 1024-sample MDCT windows (`21.33 ms` at `48 kHz`), which do not divide `30 fps` (`33.33 ms` = `1600` samples), introducing priming padding at per-segment audio splices. Finally, TTS prosody and room tone change across isolated sentence calls, and any narration wording change shifts every subsequent word timestamp anyway. Therefore, Veasy **never** splices voice by sentence: narration changes always synthesize a fresh continuous voice track and redraw every frame, while visual/timing steers reuse the cached voice and run `props.mix_audio()` once over the concatenated silent video.

---

### Domain E: Directing Small Video Edits in Plain Words

18. **Walter Murch — *In the Blink of an Eye* (The Rule of Six: Emotion, Story, Rhythm, Eye-Trace)**
    - **Source:** [Walter Murch, *In the Blink of an Eye* (Lecture Transcript Archive)](https://www.filmsound.org/murch/blink/)
    - **What it teaches Veasy:** Murch ranks **Emotion (51%)**, **Story (23%)**, and **Rhythm (10%)** at the top of every cut decision, noting that shifting a cut by 3 to 10 frames changes whether a beat feels sluggish, rushed, or inevitable. Veasy exposes this rhythm control via per-scene frame adjustments (`steer` verbs `--tighter`, `--breathe`, `--land`, and explicit `hold_adjust`).

19. **Frank Thomas & Ollie Johnston — *The Illusion of Life* (Disney's 12 Principles: Timing, Spacing & Staging)**
    - **Source:** [Twelve Basic Principles of Animation (Thomas & Johnston, 1981)](https://en.wikipedia.org/wiki/Twelve_basic_principles_of_animation)
    - **What it teaches Veasy:** **Timing** is the frame count allocated to an entrance and hold (`enter_frames`, `s["duration"]`, `hold`), whereas **Staging** limits simultaneous competing motions (`motion_rules.MAX_MOVES = 3`). Every `steer` timing edit is checked against `tt_shorts/motion_rules.py` (`read`, `still`, `pacing`, `moves`, `pingpong`) before rendering so a director's tweak never breaks readability or hold margins.

20. **Descript — Word-Anchored Transcript Editing**
    - **Source:** [Descript Documentation: Text-Based Video Editing & Word-Level Alignment](https://help.descript.com/hc/en-us/articles/10119621515277-Getting-started-with-Descript)
    - **What it teaches Veasy:** Binding visual scenes to spoken words (`at` anchors and `em` emphasis phrases) lets a user inspect each scene alongside the exact Georgian words spoken during `[s.from, s.from + s.duration)` in `<render>.room.html` and edit on-screen labels without disturbing word alignment.

21. **Motion Design Direction Vocabulary — Plain-Language Rhythm Verbs (`--tighter`, `--breathe`, `--land`)**
    - **Source:** Austin Shaw, *Design for Motion* (Routledge, 2019, ISBN 978-1138318625) & `tt_shorts/motion_rules.py` / `tt_shorts/swipe.py`
    - **What it teaches Veasy:** Editors direct pacing in plain words rather than raw frame integers:
      - `--tighter`: trims excess hold on scene `i` (`-12` frames = `-0.40s`, floored at `motion_rules` minimum readable duration `enter + need + EXIT` and `speech.MIN_SCENE[type]`), pulling the boundary or handing slack cleanly while keeping `motion_rules.check` green.
      - `--breathe`: gives scene `i` more reading air (`+15` frames = `+0.50s` by borrowing slack from adjacent scene `i+1` or `i-1` if available, or extending hold, and setting `hold="still"` if needed so the eye rests calmly).
      - `--land`: gives the key number or claim weight (`+9` frames = `+0.30s` settle hold + sets `hold="still"` and auto-marks the primary stat/headline token in `em` if unmarked so the number lands with emphasis).

---

## 2. Commercial Licence Table

All dependencies and architectural patterns used in the Edit Room comply with `CLAUDE.md` (*"Only licences allowing commercial use; record the source and licence beside every vendored file. No GPL/AGPL code"*):

| Dependency / Component | Licence | Commercial Use | How Veasy Uses It |
| :--- | :--- | :--- | :--- |
| **Python 3.12 stdlib (`hashlib`, `json`, `html`, `subprocess`, `pathlib`)** | PSF-2.0 | Yes | Core implementation of `tt_shorts/segments.py`, `tt_shorts/steer.py`, and `tt_shorts/room.py` (zero new third-party packages). |
| **HyperFrames (`heygen-com/hyperframes` v0.9.8)** | Apache-2.0 | Yes | Local CLI renderer in `compose/node_modules/hyperframes` (`--start` / `--end` partial spans). |
| **Remotion (`@remotion/cli`, `@remotion/renderer` v4)** | Remotion License | Yes (Free tier $\le 3$ people; Company license $\ge 4$) | Local CLI renderer in `remotion/node_modules` (`--frames=A-B` partial spans). |
| **FFmpeg / FFprobe CLI (`ffmpeg`, `ffprobe`)** | LGPL v2.1+ / GPL v2+ (CLI binary) | Yes (OS subprocess) | Invoked strictly as an external OS subprocess (`subprocess.run(["ffmpeg", ...])`) for concat demuxing and audio mixing; zero library linking or binary redistribution. |
| **GSAP (`gsap@3.15.0`)** | GSAP Standard No-Charge License | Yes | Bundled with HyperFrames for deterministic timeline animations. |
| **Pillow (`PIL.Image`) & `fontTools`** | MIT-CMU / MIT | Yes | Already in `.venv`; used by `golden.py`, `probe.py`, and `captions.py`. |
| **Lucide Icons (`assets/icons/lucide.json`)** | ISC | Yes | Existing icon pack with `LICENSE` beside it. |

---

## 3. Ranked Backlog (Value vs. Effort)

| Rank | Unit | Deliverable & Files Owned | Value | Effort | Evidence & Gate |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Content-Addressed Scene Segments & Splicer** | `tt_shorts/segments.py` + single additive branch in `tt_shorts/props.py:render_video` and `tt_shorts/compose.py:render`. Per-scene SHA-256 cache in `$VEASY_HOME/cache/segments/<sha16>/`, Remotion `--frames` and HyperFrames `--start/--end` partial rendering, FFmpeg `-f concat -c:v copy` splicing with automatic re-encode fallback, and single-pass `props.mix_audio`. | **Very High** | **Medium** | Changing 1 scene re-renders only 1 segment; frame hashes outside the changed scene equal a full render; `check`, `probe`, `qa`, and `flash` pass. |
| **2** | **`engine steer` CLI, `--dry` Cost Estimator & Plain Verbs** | `tt_shorts/steer.py` + `steer` subcommand in `tt_shorts/engine.py`. Implements `--scene <i|id>`, `--set field=value`, `--tighter`, `--breathe`, `--land`, and `--dry`. Pre-run cost estimator distinguishes Case A (1 scene visual change, `$0`), Case B (timing verb change checked by `motion_rules.py`, `$0`), and Case C (narration change -> `"new voice, every frame"`). Parity across Remotion and HyperFrames. | **Very High** | **Medium** | `--dry` is tested and accurate on a text change, a timing change, and a narration change; timed benchmark on `demo/film-partia.json` shows before/after wall-clock savings. |
| **3** | **The Edit Room Page (`<render>.room.html`)** | `tt_shorts/room.py` + `room` subcommand in `tt_shorts/engine.py` + auto-generation alongside renders/steers. Self-contained dark-canvas HTML page showing every scene's still, on-screen words, spoken words, frame/second timing, reading rhythm load (`motion_rules`), pre-run cost table, and one-click copyable `engine steer` commands. | **High** | **Low–Med** | `<render>.room.html` opens cleanly, renders every scene's still and metrics, and the Fresh-Eye Critic sub-agent fixes a scene using `<render>.room.html` and `skills/steer/SKILL.md` alone. |
| **4** | **Skill `veasy:steer` & Hermes Plugin Tool `veasy_steer`** | `skills/steer/SKILL.md` (< 12,000 chars), `.claude/skills/steer` link (mode `120000`), `plugin.yaml` (`veasy_steer`), `__init__.py` (`TOOLS`), and `tests/test_steer.py` + `docs/research/edit-room-result.md`. | **High** | **Low** | `tests/test_plugin.py`, `tests/test_steer.py`, `npx tsc --noEmit`, and `python -m tt_shorts.engine selftest` all pass green. |
