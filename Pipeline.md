**Goal:** One command, script in, video out. No GUI prompting, no IDE bloat. CLI-native long-form video production.

**Core architecture:** YAML DSL → Python orchestrator → ElevenLabs TTS → Remotion/Kdenlive compositions → rendered video

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

  # Natural language edit block — describe the edit in natural language, LLM interprets and turn into Remotion code
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
      split screen — three panels left to right, staggered 0.3s, the one on the left comes from the bottom, the one of the right comes from the top.
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
| `e:` | `edit:` | Natural language block. LLM interprets and generates Remotion code. |
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
      split screen — three panels left to right, staggered 0.3s.
      clean white dividers.
    media:
      - assets/source1.png
      - assets/source2.png
      - assets/source3.png
```

---

## Version 1 — Generate & Assemble (MVP)

**What it does:** Parses YAML, generates all narration, generates subtitle files, generate custom edits made with Remotion, writes a Kdenlive project file with everything loaded on tracks. You arrange manually.

**What it solves:** Eliminates the TTS generation grind and the blank-timeline-start problem. You open Kdenlive and everything is there waiting to be arranged.

**EXPERIMENTAL:** You can also generate/describe Kdenlive effects.

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
                             (unsynced — just loaded in order)
    │
    ▼
[5] Open in Kdenlive ─── arrange media to match narration
                          fill blank spaces manually
                          add effects/transitions by hand
                          export
```

### Key notes
- **ElevenLabs char limit:** Split narration at YAML entry boundaries. If a single narration entry exceeds char_lim (by default 5000), split at sentence boundaries.
- **MLT XML structure:** Producers (media files) → Playlists (tracks) → Tractor (multitrack composition). Clips have `in`/`out` in frame numbers = timestamp × fps.

## Version 2 — Automated Sync via ElevenLabs timestamps 

**What it adds:** Uses ElevenLabs' `/stream/with-timestamps` endpoint to get character-level timing data. Media cues from the YAML are synced to specific words/phrases in the narration automatically.

**What it solves:** Eliminates manual arrangement. The rough cut is already synced when you open it.

### New in the pipeline

```
[2] changes to:
    ElevenLabs /stream/with-timestamps
        → audio chunks (base64 assembled)
        → character-level timing map

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

## Version 3 — LLM-Generated Remotion/Kdenlive compositions

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
- **LLM reliability:** Generated Remotion code might sometime break. Keep a cache of known-good compositions for common effects (carpet transition, glitch, fade, etc.) and only hit the LLM for novel descriptions.
- **Effect library over time:** As you accumulate working compositions, you build a personal library. The LLM becomes a fallback for new effects, not the primary path.

## Version 4 — MPV Interactive Preview & Re-prompting

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
    │     if code:
    │         let the user rewrite the corresponding lines from the .jsx
    │
    ├── resume playback
    │
    └── on completion: write final .kdenlive / render via Remotion
```

---

## Dependencies
### Python :
pyyaml elevenlabs requests
(?) lxml
anthropic API
### Software :
kdenlive
mpv 
ffmpeg / ffprobe
### Webshit :
remotion / node.js

---

## More tentative features :
- Use a video/clip example as inspiration for the effect you want to generate, instead of just natural language 
- Dynamically integrate media as links(e.g from youtube, soundcloud, etc...) instead of relying putting raw files from hard drive.
