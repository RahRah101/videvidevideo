**Goal:** One command, script in, video out. No GUI prompting, no IDE bloat. CLI-native long-form video production.

**Core architecture:** YAML DSL => Python orchestrator => ElevenLabs TTS => Remotion/Kdenlive compositions => rendered video

> vvv is a deterministic script-to-video tool and backend-agnostic: YAML DSL -> vvv (acquisition, ElevenLabs TTS, stems, timing) => **pluggable assembler** => editor project / rendered video. Assemblers today: Kdenlive via KdenCLI (working). Current focus: a HyperFrames (HTML/CSS => MP4) assembler, which takes the place Remotion had in this doc. When targeting HyperFrames, vvv compiles the deterministic 90% (zero tokens), HyperFrames does timeline/effects/render, and an agent only touches `e:` blocks one chunk at a time. Status: V1 proven on Kdenlive (158 nodes, ~1 hr). Plan: `TODO.md` Phase 1–5.

---

## YAML DSL (The Script Format)

The DSL is the foundation everything else builds on. Every version of the pipeline reads from this format.

### Shorthand (what you actually write)

Designed for speed. A preprocessor expands this into the full YAML before the pipeline touches it.

```yaml
meta:
  title: "Video Title Here"
  voice: "elevenlabs_voice_id"
  char_lim: 5000
  fps: 30
  res: [1920, 1080]

s:
  - n: Opening line of narration goes here.

  - n: And then we see the clip in question.
  - v: video.mp4 [1:01-1:06]

  - n: Now look at this image.
  - i: image.png -> image2.png {carpet}

  - n: This is where everything falls apart.
    @falls apart: {glitch}

  - n: And we sit with that for a moment.
  - _: 2  # pause, seconds

  - t: "CHAPTER 2" 3s {title_card}

  # Natural language edit block - describe the edit in natural language, LLM interprets and turns into Remotion code
  - n: He grew up surrounded by concrete and noise.
  - e: >
      slow pan across a grainy photo of a neighborhood.
      desaturate everything except the red.
      slight film grain overlay. melancholic energy.
    +: neighborhood.jpg
    d: 6

  - n: And then the beat drops.
  - e: >
      hard cut to the music video clip. bass-heavy shake on impact,
      screen rattling from the sub. flash of white then slam in.
    +: mv_clip.mp4 [0:32-0:38]

  - n: This is the part nobody talks about.
    @nobody: >
      zoom into the speaker's face real slow.
      vignette creeps in. background blurs progressively.

  - n: Three different sources. All saying the same thing.
  - e: >
      split screen - three panels left to right, staggered 0.3s, the one on the left comes from the bottom, the one on the right comes from the top.
      clean white dividers.
    +:
      - source1.png
      - source2.png
      - source3.png
```

### Shorthand key

| Short | Expands to | Notes |
|-------|-----------|-------|
| `s:` | `script:` | |
| `n:` | `narrate:` | Narration text. |
| `v:` | `clip:` | Video. Timestamps in `[from-to]`. |
| `i:` | `image:` | `->` for transitions between images. `{effect}` for transition type. |
| `e:` | `edit:` | Natural language block. LLM interprets and generates Remotion code. (HyperFrames: a sub-composition.) |
| `t:` | `text_overlay:` | Text, duration, optional `{style}`. |
| `_:` | `pause:` | Seconds of silence. |
| `+:` | `media:` | Asset path(s) attached to an `e:` block. Timestamps in `[from-to]`. |
| `d:` | `duration:` | Seconds. |
| `@word:` | `on_word:` | Triggers effect/edit at a specific word. `{effect}` for presets, or `>` block for natural language. |
| `{name}` | Named preset effect | Curly braces = predefined effect from your personal library. |
| `[1:01-1:06]` | `from/to` | Inline timestamp range. |
| `->` | Transition | `a.png -> b.png` = transition from one to the other. |

### Full YAML (what the pipeline reads)

The preprocessor (`expand.py`) converts shorthand into this format. The rest of the pipeline only ever sees YAML.

```yaml
meta:
  title: "Video Title Here"
  voice_id: "elevenlabs_voice_id"
  char_lim: 5000
  fps: 30
  resolution: [1920, 1080]
  assets_dir: "assets/"  # prepended to all relative paths

script:
  - narrate: "Opening line of narration goes here."

  - narrate: "And then we see the clip in question."
  - clip: assets/video.mp4
    from: "1:01"
    to: "1:06"

  - narrate: "Now look at this image."
  - image: assets/image.png
    transition: carpet
    to: assets/image2.png

  - narrate: "This is where everything falls apart."
    on_word: "falls apart"
    effect: glitch

  - narrate: "And we sit with that for a moment."
  - pause: 2.0

  - text_overlay: "CHAPTER 2"
    duration: 3.0
    style: title_card

  - narrate: "He grew up surrounded by concrete and noise."
  - edit: >
      slow pan across a grainy photo of a neighborhood.
      desaturate everything except the red.
      slight film grain overlay. melancholic energy.
    media: assets/neighborhood.jpg
    duration: 6.0

  - narrate: "And then the beat drops."
  - edit: >
      hard cut to the music video clip. bass-heavy shake on impact,
      screen rattling from the sub. flash of white then slam in.
    media: assets/mv_clip.mp4
    from: "0:32"
    to: "0:38"

  - narrate: "This is the part nobody talks about."
    on_word: "nobody"
    edit: >
      zoom into the speaker's face real slow.
      vignette creeps in. background blurs progressively.

  - narrate: "Three different sources. All saying the same thing."
  - edit: >
      split screen - three panels left to right, staggered 0.3s.
      clean white dividers.
    media:
      - assets/source1.png
      - assets/source2.png
      - assets/source3.png
```

---

## Version 1 - Generate & Assemble (MVP)

**What it does:** Parses YAML, generates all narration, generates subtitle files, generates custom edits made with Remotion, writes a Kdenlive project file with everything loaded on tracks. You arrange manually.

**What it solves:** Eliminates the TTS generation grind and the blank-timeline-start problem. You open Kdenlive and everything is there waiting to be arranged.

**Status:** ✅ Done on the Kdenlive target (acquisition from local/URL/YouTube, per-line voice override, stems). Subtitles not generated yet. Not yet ported to HyperFrames.

**EXPERIMENTAL:** You can also generate/describe Kdenlive effects(as kdencli supports(untested) kdenlive effects).

### Pipeline

```
script.yaml
    │
    ▼
[1] Parse YAML ─── extract narration chunks
                    extract media references
    │
    ▼
[2] ElevenLabs TTS ─── for each narration chunk:
                          POST /v1/text-to-speech/{voice_id}
                          save audio as chunk_001.wav, chunk_002.wav, ...
    │
    ▼
[3] Generate subtitles ─── for each audio chunk:
                             use ElevenLabs /stream/with-timestamps
                             OR whisper with word_timestamps=True
                             save as chunk_001.srt, chunk_002.srt, ...
    │
    ▼
[4] Write .kdenlive XML ─── create producers for all assets
                             (audio chunks, video clips, images)
                             place audio sequentially on track 1
                             place subtitles on track 2
                             place media references on track 3
                             (unsynced - just loaded in order)
    │
    ▼
[5] Open in Kdenlive ─── arrange media to match narration
                          fill blank spaces manually
                          add effects/transitions by hand
                          export
```

**With the HyperFrames target, steps [4]–[5] become:**
```
[4] Assemble (target from config: kdenlive | hyperframes | any plugin)
    hyperframes: emit index.html root composition
                 one sub-composition per chapter
                 <audio>/<video>/<img>/titles with data-start / data-duration /
                 data-track-index computed by vvv (absolute, frame-quantized)
                 clips keep their own audio (no A/V split)
                 `hyperframes lint` before handing off
[5] Open in HyperFrames Studio / preview ─── arrange, tweak, render
```

### Key notes
- **ElevenLabs char limit:** Split narration at YAML entry boundaries. If a single narration entry exceeds char_lim (by default 5000), split at sentence boundaries.

### Kdenlive integration: two approaches

**Option A - OpenTimelineIO (OTIO)**
- Python API for building timelines: `Track`, `Clip`, `Transition` objects instead of raw XML.
- `pip install opentimelineio` + the Kdenlive adapter (`pip install otio-kdenlive-adapter`).
- Cleaner code - no manual producer ID management or XML nesting.
- Future-proofs the project: OTIO also exports to DaVinci Resolve, Final Cut Pro XML, AAF, EDL, etc. Swap editors without rewriting timeline generation.
- **Caveat:** The Kdenlive adapter is noted as unstable and lagging behind Kdenlive's newer features. For basic clip/audio placement this is fine. For Kdenlive-specific filter chains, it won't help - but that's what Remotion handles anyway.
- **Caveat:** OTIO handles cut structure (placement, ordering, durations, basic transitions), not effects. Complex effects stay in the Remotion layer.

**Option B - Raw MLT XML**
- Direct control over everything Kdenlive supports, including all effects and filter chains.
- MLT XML structure: Producers (media files) => Playlists (tracks) => Tractor (multitrack composition). Clips have `in`/`out` in frame numbers = timestamp × fps.
- More brittle - IDs must be internally consistent, schema can shift between Kdenlive versions. Silent failures when something is off.
- Best approach: export a test project from Kdenlive manually and use that XML as your structural template.
- Better for the experimental Kdenlive effects generation path where the LLM writes filter/transition nodes directly.

**Chosen:** Option B, raw MLT XML via KdenCLI. Confirmed brittle the hard way (unique kdenlive:id across ALL top-level elements, stale template transitions, tracksCount) - all fixed. OTIO parked indefinitely.

**HyperFrames target notes**
- vvv emits HTML from templates; it doesn't drive `@hyperframes/sdk` for generation.
- Round-trip contract: vvv owns the root composition and regenerates it freely; agent work lives in sub-compositions vvv references but never writes; Studio/hand tweaks persist as Embedded Override deltas. Deterministic (content-hash) element IDs keep references and overrides stable.
- Costs: Node 22+; render ~1–2.5* realtime (1–2.5+ h for an hour) => chunk by chapter; offline viability must be verified (Studio desktop app wants a HeyGen sign-in).

---

## Version 2 - Automated Sync via ElevenLabs Timestamps

**What it adds:** Uses ElevenLabs' `/stream/with-timestamps` endpoint to get character-level timing data. Media cues from the YAML are synced to specific words/phrases in the narration automatically.

**What it solves:** Eliminates manual arrangement. The rough cut is already synced when you open it.

**Status:** Not started (sync phase is a stub). Much easier with HyperFrames: `on_word` = a tween at time t, captions = generated elements (using canonical text from the pronunciation layer, not TTS spelling). Cache alignment JSON next to each narration mp3.

### New in the pipeline

```
[2] changes to:
    ElevenLabs /stream/with-timestamps
        => audio chunks (base64 assembled)
        => character-level timing map

[new step] Build sync map:
    for each media entry in YAML:
        find its position relative to narration entries
        if on_word specified:
            look up word in narration text
            map to character offset
            get timestamp from ElevenLabs timing data
        else:
            place immediately after preceding narration chunk ends

[4] changes to:
    Write .kdenlive XML with media placed at synced timestamps
```

---

## Version 3 - LLM-Generated Remotion/Kdenlive Compositions

**What it adds:** Effect/transition descriptions from YAML are sent to an LLM (Claude API) which generates Remotion component code. Those render as video clips that get placed on the timeline.

**What it solves:** Programmatic effects without having to write in the horror that is JS/React, or having to open Kdenlive. Your DSL describes the effect in natural language or shorthand, the LLM translates.

**Note:** Remotion part is more developed. Can describe more complex effects and get more predictable results. Kdenlive implementation can easily break.

### New in the pipeline

```
[new step] For each media entry with effects:
    construct prompt from YAML entry
        include: effect name/description, duration, asset paths, timestamps
    send to Claude API
    receive Remotion component code
    write to remotion_project/src/compositions/effect_{i}.tsx
    run: npx remotion render effect_{i} output/effects/effect_{i}.mp4

[4] now includes rendered effect clips as additional producers
```

### Notes
- **LLM reliability:** Generated Remotion code might sometimes break. Keep a cache of known-good compositions for common effects (carpet transition, glitch, fade, etc.) and only hit the LLM for novel descriptions.
- **Effect library over time:** As you accumulate working compositions, you build a personal library. The LLM becomes a fallback for new effects, not the primary path.

**Same idea, HyperFrames instead of Remotion:**
```
[new step] For each `e:` block / unknown {preset}:
    key = hash(description + media + range + duration)
    if accepted edit cached under key: reference it, done
    else:
        prompt: description, media, duration, neighbouring narration, house style
        agent writes edits/<id>.html (sub-composition)
        `hyperframes lint`, preview the chunk, accept => cache under key
[4] root composition references edits/<id>.html - vvv never writes into it
```
- Token budget: the agent sees one chunk, never the full hour.
- First preset family: big-head South Park edits (remove-background cutout + scale + shake, parameterised).

---

## Version 4 - MPV Interactive Preview & Re-prompting

**What it adds:** Forks an MPV player via JSON IPC. Plays the rough cut, pauses at cue points (especially blank spaces), lets you re-prompt/re-write effects or fill in gaps interactively from the terminal.

**What it solves:** The "blank spaces" problem. Human editorial judgment happens inline during preview, not in a separate editing session.

### Architecture

```
Python orchestrator
    │
    ├── spawns MPV with --input-ipc-server=/tmp/mpv-socket
    │
    ├── sends playback commands via JSON IPC:
    │     { "command": ["set_property", "pause", true] }
    │     { "command": ["seek", timestamp, "absolute"] }
    │
    ├── at each cue point / blank space:
    │     pause playback
    │     print context to terminal
    │     prompt user: [a]ccept / [r]e-prompt / [f]ill / [c]ode / [s]kip
    │
    │     if re-prompt:
    │         read new description from stdin
    │         regenerate Remotion clip via LLM
    │         hot-swap in timeline
    │
    │     if fill:
    │         read media path or effect description
    │         generate and insert
    │
    │     if code:
    │         let the user rewrite the corresponding lines from the .jsx
    │
    ├── resume playback
    │
    └── on completion: write final .kdenlive / render via Remotion
```

For the HyperFrames target this is largely covered by HyperFrames preview + Studio (timeline move/trim/split, agent editing via the SDK; edits persist as Embedded Override deltas). 

---

## Version 5 - New Media Sources & Gap-Fill

**What it adds:** Gen AI backends beyond ElevenLabs (image, video, diagram, speech) plugged in as ordinary backends/directives, programmatic visual descriptions directly in the script, plus a `vvv fill` mode that proposes generations for the blank spaces left after V2 sync.

**What it solves:** The blank-spaces problem again, without handing the thinking to the machine. You write the script, AI only proposes b-roll for gaps, and every proposal lands in the script where you can edit or veto them. Middle ground between creativity/agency and productivity.

### New in the pipeline

```
No new "generator" layer: everything that produces media already is one
(yt-dlp, ElevenLabs, x-minus, titles). New sources are just more
backends/directives in the existing directive => Producer => backend pattern.

[any nondeterministic producer]
    key = hash(prompt/spec + seed + backend + model version + params)
    if pinned in vvv.lock: reuse file, done
    else: generate => accept => pin in vvv.lock

[e: edits/animations]
    routed:    via: <backend> => straight to a specific model/tool (default)
    delegated: agent gets the available backends as tools, can combine them (opt-in)

[new command] vvv fill script.yaml        (needs V2 word timestamps)
    for each narration span with no visual:
        plan a shot spec from the synced narration (cheap text-only LLM, can be local)
        write proposed entries (normal directives) INTO the script (or a sidecar YAML)
    => you review / edit / delete => vvv build as normal
```

```yaml
# candidate shapes only, not decided
- i: { prompt: "...", via: qwen-image, seed: 42 }   # image from a prompt
- diagram: { via: archify, spec: {...} }            # programmatic, zero tokens
- e: "big head shake on the punchline"
  via: agent                                        # delegated, opt-in
```

### Notes
- **Determinism comes from the cache, not the model.** APIs never reproduce (ElevenLabs included); local models only with a fixed seed. The lock file is what keeps vvv deterministic.
- **What's actually new:** pinning + a human accept step for nondeterministic outputs, and HTML sub-compositions as a media kind (HyperFrames places them natively; kdencli needs them pre-rendered to mp4).
- **LLM ladder:** hand-written spec => template + your values => LLM fills a small spec => agent free-form. Only climb as far as needed.
- **Skills are mostly a renderer with instructions on top.** archify (typed JSON IR + Node CLI), diagram-design (HTML/SVG templates, Mermaid import), anatomy (JS/SVG/WebGL kit). vvv can call the renderers directly and skip the token burn. All output HTML, so they drop into HyperFrames as sub-compositions.
- **Offline rule:** render + cache must work offline; generation may need the network, same as acquisition.
- **Presets before skills:** accepted edits saved with parameters cost zero tokens. A skill only for "make a new one in this style", after 3+ similar accepted edits.
- **Keep fills obviously graphic** (diagrams, typography, textures, big-head edits). Real people stay real footage; YouTube requires disclosure for realistic synthetic content.

---

## Dependencies

### Python
- pyyaml
- elevenlabs
- requests
- anthropic
- jinja2 (for Hyperframes target)
- demucs (public stem backend)
- gen AI backends as needed (diffusers / API SDKs), optional

### Software
- Kdenlive
- MPV
- FFmpeg / FFprobe
- librubberband
- yt-dlp + Deno 

### Webshit
- Remotion
- Node.js
- Hyperframes CLI 

---

## Tentative Future Features

- **Visual reference for effects:** Use a video/clip example as inspiration for the effect you want to generate, instead of just natural language description.
- **Pronunciation layer:** canonical text vs TTS spelling, applied only at the TTS step. Required before captions.
- **Distributed render** (HF Lambda / Cloud Run) - only if local chapter renders are too slow. Conflicts with offline-first, so last resort.
