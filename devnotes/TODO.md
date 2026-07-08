## Track model
* [ ] Kill the hardcoded VIDEO/TTS/AUDIO_TRACK in the assembler. This is dumb as hell.
    * Default = auto-allocate by kind (kdencli has FindOrCreateTrack).
    * Explicit = `track: <name>` in DSL → assembler name→id map, create-once-reuse
  (step-2 control layer on top of auto-allocation).
* [ ] Note : sync phase is still a stub -> A/V-split audio lands on the audio track WITHOUT positional blanks, so clip audio + narration jumble on one track. Root cause is kdencli A/V split not being position/room-aware (must emit a leading blank matching the video half's timeline position).
---

## Caching
Current caching behavior is crude and garbage. Use hashing.
* [ x ] **Narration** - `out.exists()` guard skips the ElevenLabs call. WORKS.
  * [ ] TODO: upgrade key from counter to CONTENT HASH. Key on `hash(text + voice_id)[:8]` 
* [ ] **Stems**
    * [ ] Proper key: `hash(source + range + stems + model)`.
* [ ] **Video download** = `--no-overwrites` isn't enough. Fix cleanly with yt-dlp's own `--download-archive build/media/.archive.txt`, so then we can check a local ID list FIRST, skipping WITHOUT hitting youtube 
* [ ] **BIG unify**: one content-addressed `Cache` abstraction all producers use, `key = hash(inputs); if cache.has(key): return; else do_work(); cache.put(key)`. Identity by content-hash.

---

## Acquisition efficiency
* [ ] `--download-sections *from-to` — only fetch the clipped RANGE, not the whole thing and then call ffmpeg to cut, when there is a trim directive. 
* [ ] Quality - Let DSL override per-clip whatever quality is downloaded from the online clip

---

## Observability (NEW)
* [ ] Structured progress logging in resolve: `[resolve] node 47/158: <action> <source>`

---

## Filenames (NEW)
* [ ] yt-dlp output template `%(title)s [%(id)s].%(ext)s` (not bare `%(id)s`) so the editor bin shows real names instead of cryptic IDs. `[id]` suffix keeps cache-key uniqueness. Truncate long titles; `--restrict-filenames` sanitizes.

---

## Pre-flight validation
* [ ] A standalone validator that checks a yaml WITHOUT spending credits/downloads with whatever is sensitive to data/credit usage

---

## DSL extensibility (decouple nodes/parser like producers)
* [ ] Adding a directive currently requires editing CORE files (`ir/nodes.py` + `phases/ parse.py`). Garbage.
    * A directive should be a self-contained plugin = node + parse-handler (registered by key) + producer, all from outside core.
    * Build a parse-handler registry (key => fn, dispatched in `_parse_entry` the way
  producers dispatch by node_type).
    * Then directives plug in via entry points like stem backends do.
    * Just copy the producer/backend registration pattern to be honest. That's literally it

---

## Config layer
* [ ] ElevenLabs voice + stem backend are hardcoded/env-var. Need real config.
    * Per-project (meta in YAML) + global config file.
    * Backend selection (stem, TTS), API keys, kdencli path, default fonts/tracks.
    * composition.py reads config instead of hardcoding shit.

---

## Snippets, variables, macros

### 1. Snippets
* [ ] A `defs:` block in the USER's YAML
    * Parse reads `defs` into a runtime macro table.
    * `use: name args: {...}` expands the snip body (substitute params); body entries
  recurse through `_parse_entry` so snips compose.
    * Pure text/template expansion at parse time => plain nodes.

### 2. Variables = dataflow between nodes (extras-binding, NO scripting)
* This is the ONLY thing that made snippets feel "programmatic"; solving it separately
  keeps snippets purely declarative.
* [ ] Static vars: parse-time env + substitution.
* [ ] Dynamic source: `as: <name>` binds a node's RESOLVED extras to a name in ctx.bindings; `{name.field}` placeholders in ANY field reference a binding; a SUBSTITUTION pass after RESOLVE (value now known) before/at assemble fills them.

For example, this could be used for a copyright snippet to give credits on queried videos from youtube :
```yaml 
    # def (snippet)
def cite(artist, url, ts):
  - stem: "{url} {ts}"
    stems: [vocals]
    as: src                          # variable binding
  - title: "{artist} - {src.title} ({src.date})"   # variable reference

# use 
- use: cite("Artist Name", "youtu.be/...", "[0:22-0:31]")
```

### 3. Lua 
TODO 
---

## Probe consolidation (BANK)
* [ ] Consolidate the à-la-carte probe fns (has_audio_stream / has_video_stream / probe_duration / …) into one `probe(path) -> MediaInfo{has_video, has_audio, duration, is_image}`. One ffprobe call, one struct; kills scattered imports + triple-probe waste. (The image-duration and audio-routing bugs both came from these being separate.)

---

## TextMetrics cross-platform
* [ ] Currently fontconfig (fc-match) on Linux + FreeType. Only estimates for Mac/Windows.
* [ ] `--font-file` override (FreeType is cross-platform; bypasses fc-match).
* [ ] Later: CoreText (Mac) / DirectWrite (Windows) resolvers

---

## Stem backend completion
* [ ] Finish `LocalDemucs.separate()` (the public reference backend is still a STUB, mostly because I can't test LocalDemucs as I do not have a powerful GPU, so far only stem backend tested is an unexposed script using that bots some online platform that offers stem separation)

---

## Pronunciation layer (BANK)
* [ ] Separate canonical text from TTS-spelling. Currently phonetic hacks are inline in the script, which corrupts the text for any non-audio use (captions, display). Build a pron-map (canonical => TTS-spelling / SSML / phonemes) applied ONLY at the narrate/TTS step. Keeps source text canonical, fixes pronunciation.

