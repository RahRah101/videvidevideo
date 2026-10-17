# vvv - TODO / devnotes

## Where things stand
* [x] V1 works end to end on Kdenlive: a real 158-node script, ~1 hr timeline, opens clean in Kdenlive.
* [x] KdenCLI corruption fixed (kdenlive:id scan over ALL top-level elements, ReconstructState after DeletePreExistingTracks, stale template transitions deleted, tracksCount sync, tracks inserted before transitions).
* [x] Per-narrate voice override, image URLs, audio-only clip routing, YouTube n-challenge.
* [ ] Sync is still a stub -> arrangement is manual.

---

## Identity & current focus
**vvv is a deterministic script-to-video tool, backend-agnostic by design.** Assemblers are plugins; anyone can point it at whatever editor/renderer they want. That doesn't change.

**Current focus: a HyperFrames assembler.** HyperFrames (HeyGen, Apache 2.0) is a full HTML/CSS video editor (timeline attrs, nested compositions, Studio NLE, CLI render) with effects, motion, text and agent editing native - this shit is a fight in MLT XML. It's what we are trying now, added *alongside* kdencli, not replacing it.

How the layers split when targeting HyperFrames:

| Layer | Owns | Cost |
|---|---|---|
| **vvv** | Script -> deterministic skeleton: acquisition, ElevenLabs narration (per-line voices), stems, timing, captions, cached everything | vvv itself costs nothing; the backends it calls (ElevenLabs, stems, gen AI) may cost credits - your choice. Cheap, repeatable |
| **HyperFrames** | Timeline, rendering, effects/motion, preview, hand edits (Studio) | compute only |
| **Agent** | Only `e:`/`edit:` blocks + creative passes on ONE chunk at a time | tokens - spent only where an LLM is actually worth it |

vvv's value is explicit: 90% of an hour-long essay is narration + clips + images in order. Doing that with an agent burns tokens to reproduce what a compiler does for free. vvv compiles the boring 90%; the agent touches the 10% that needs taste.

Guardrail: core phases (parse/resolve/sync) stay assembler-neutral. Anything HyperFrames-specific lives in its assembler plugin.

**Drop-the-HyperFrames-backend criteria** (if the spike shows any of these, stop investing in it and keep shipping through kdencli; all untested - the spike checks them; render goes through the CLI, Studio is optional):
* core preview/render can't run fully offline
* a 1-hour project is unworkable in preview/CLI render even when chunked by chapter
* render time is so bad that chapter-level re-renders don't fix it

---

## Phase 1 - HyperFrames assembler plugin
* [ ] `assemblers/hyperframes/` behind the same Assembler interface as KdencliAssembler; chosen by config / `--target hyperframes|kdenlive`. Neither is "the default" in principle - default comes from config.
* [ ] Emit HTML from Python with templates (Jinja2).
* [ ] Node -> element mapping:
  * [ ] narrate -> `<audio>` (data-start, data-duration, track)
  * [ ] clip -> `<video>` carrying its own audio (source offset, volume, playback rate). **The A/V-split / missing-blank jumble does not exist in this backend.**
  * [ ] image -> `<img>` with explicit data-duration
  * [ ] title -> styled element; `{style}` presets = CSS classes in a stylesheet
  * [ ] stem -> `<audio>`
  * [ ] pause -> gap in computed timing
* [ ] Timing: vvv computes ABSOLUTE starts (it already probed every duration). Keeps the HTML dumb and diffable. HF relative starts (`intro + 0.5`) are tempting but make override anchors fragile - verify before using them.
* [ ] Tracks -> `data-track-index`, implementing the core Track model below.
* [ ] Frame-quantize all times on emit (HF works in seconds; integer frames avoid drift).
* [ ] **Chapter chunking**: one sub-composition per chapter/section (chapter directive or `# ---` markers). Render/preview/agent-edit per chunk, concat with ffmpeg. An hour in one flat HTML file is asking for pain.
* [ ] Run `hyperframes lint` as part of `vvv build` - the HF equivalent of the KdenCLI Validate() we never built, for free.

---

## Phase 2 - Round-trip contract
Kdenlive was one-shot: generate once, hand-edit, never regenerate. HyperFrames lets regeneration and hand edits coexist **only if ownership is explicit**:
* [ ] vvv owns the root composition + timing skeleton. Regenerated freely; never edited by hand.
* [ ] Agent/creative work lives in agent-owned sub-compositions (`edits/<id>.html`) that vvv REFERENCES and never writes.
* [ ] Studio/human tweaks (move, trim, nudge) persist as an **Embedded Override** delta over the vvv base, not as edits to the base file.
* [ ] Deterministic element IDs from a position-independent content key (same hashing as the cache) so references and overrides survive script edits/reordering. Helper exists: `ir/ids.element_ids(nodes)` (content key + occurrence index for identical lines), nothing uses it yet.
* [ ] Verify: does an override survive a base regen when IDs are stable? Orphaned overrides (target removed) -> warn loudly, never drop silently.
* [ ] Rule: if you're hand-editing vvv's generated `index.html`, the contract is broken - fix the DSL or the override instead.

---

## Phase 3 - Agent edits (old Pipeline V3, now cheap)
* [ ] `e:`/`edit:` -> agent prompt with: description, media, duration, neighbouring narration for context. Output = one sub-composition file.
* [ ] Cache accepted edits by `hash(description + media + range + duration)`; never regenerate an accepted edit.
* [ ] Preset library: `{name}` effects = accepted sub-compositions / CSS+GSAP snippets in a user dir. Agent is the fallback for novel descriptions only.
* [ ] Token budget: the agent sees one chunk, never the whole hour.
* [ ] Will try with big-head edits as a parameterised preset family (cutout + scale + shake + timing).

---

## Phase 4 - Sync (old Pipeline V2, much easier under HF)
In HTML, `on_word` is just a tween at time t and captions are just elements. This was hard on Kdenlive; it's the highest-value feature left.
* [ ] Narration via ElevenLabs `/with-timestamps`; cache alignment JSON next to the mp3 (same cache key).
* [ ] `@word:` -> absolute time -> element data-start / GSAP tween.
* [ ] Generated caption track from alignment - using CANONICAL text from the pronunciation layer, not TTS spelling ("Vybz Kartel", not "Vibes Kartel").
* [ ] Media placement after preceding narration ends = the V2 sync map; replaces the stub.

---

## Phase 5 - Gap-fill mode (needs Phase 4 sync + New media sources below)
Middle ground between creativity/agency and productivity, not AI slop: you write the script (the analysis is the product), AI only fills b-roll gaps, and every fill is visible + vetoable in the script.
* [ ] `vvv fill <script>`: find narration spans with no visual (needs word timestamps), plan a shot spec per gap (cheap text-only LLM, could be local), WRITE proposed entries (normal directives) into the script (or a sidecar YAML). Never drop generated media straight into the timeline.
* [ ] You review/edit/delete the proposals, then `vvv build` as normal.
* [ ] This is the delegated mode below: the agent gets creative with whatever tools are available.
* [ ] Default fills to obviously-graphic stuff (diagrams, typography, textures, big-head edits). Real people stay real footage.

---

## vvv core

## Track model
* [ ] Kill the hardcoded VIDEO/TTS/AUDIO_TRACK in the assembler. This is dumb as hell.
    * Default = auto-allocate by kind (kdencli has FindOrCreateTrack).
    * Explicit = `track: <name>` in DSL -> assembler name->id map, create-once-reuse
  (step-2 control layer on top of auto-allocation).
    * Backend-neutral: core just passes `track:` names through; each assembler maps them (kdencli -> track ids, HyperFrames -> `data-track-index`).
* [ ] Note : sync phase is still a stub -> A/V-split audio lands on the audio track WITHOUT positional blanks, so clip audio + narration jumble on one track. Root cause is kdencli A/V split not being position/room-aware (must emit a leading blank matching the video half's timeline position).
---

## Caching
Current caching behavior is crude and garbage. Use hashing.
* [ x ] **Narration** - `out.exists()` guard skips the ElevenLabs call. WORKS.
  * [x] TODO: upgrade key from counter to CONTENT HASH. Key on `hash(text + voice_id)[:8]` 
    * Put a separator between them: `hash(text + "\x00" + voice_id)` so `"ab"+"c"` != `"a"+"bc"`. Filename `narrate_{NNN}_{hash8}.mp3` keeps human ordering.
    * Done: key = text + voice + `TTSBackend.cache_identity()` (ElevenLabs adds `model_id`), canonical JSON instead of the `\x00` separator, 16 hex. Filename `narrate_{NNN}_{key}.mp3`; lookup is by key only, so reordering reuses the audio. One cache entry per chunk: a run that dies midway only redoes the missing chunks.
    * Old `narrate_NNN.mp3` files stop the run before any ElevenLabs call. To reuse them (assumes your script hasn't changed since), add `config: { narrate: { adopt_legacy: true } }` to the script, run once, then remove it.
* [ ] **Stems**
    * [ ] Proper key: `hash(source + range + stems + model)`.
    * [ ] The existing `[skip] exists` check fires too late - after re-encode + re-upload + the full x-minus job. Hoist it to the top of the routine. (that check lives in the external backend, not in this repo)
* [ ] **Video download** = There's a crude `<id>.*` pre-check now (YouTube IDs only, partial downloads ignored), but it's not enough. Fix cleanly with yt-dlp's own `--download-archive build/media/.archive.txt`, so then we can check a local ID list FIRST, skipping WITHOUT hitting youtube 
* [x] **BIG unify**: one content-addressed `Cache` abstraction all producers use, `key = hash(inputs); if cache.has(key): return; else do_work(); cache.put(key)`. Identity by content-hash.
    * Done: `util/cache.py` - `cache_key(kind, **inputs)` + `Cache(dir).get_or_make(key, make, prefix, suffix)`. `make` writes a temp file that is renamed into place only when it finishes, so an interrupted run never leaves a broken file that looks cached. Used by narration, image URLs (keyed on URL: no re-download, no basename collisions, warm rebuilds offline) and trim (keyed on abs path + size/mtime + range: no collisions across directories, replacing the source invalidates).
    * [ ] Not on it yet: video downloads (see above), stems' separation step (lives in the backend).
    * [x] "inputs" = everything that changes the output: prompt/spec + seed + backend + model version (+ params). Narration too: add the ElevenLabs `model_id` to its key, switching models changes the audio.
    * [ ] For backends that never reproduce (APIs, ElevenLabs itself), the cache IS the determinism: pin accepted outputs in a lock file (`vvv.lock`). Rebuilds reuse the pin; regenerate only when explicitly asked.

---

## Acquisition efficiency
* [ ] `--download-sections *from-to` - only fetch the clipped RANGE, not the whole thing and then call ffmpeg to cut, when there is a trim directive. 
* [ ] Quality - Let DSL override per-clip whatever quality is downloaded from the online clip
    * Optional global `max_height` in config (a 1080p cap would have made a ~30 GB 4K source ~1/4 the size). Default stays best-available.

---

## Observability (NEW)
* [ ] Structured progress logging in resolve: `[resolve] node 47/158: <action> <source>`

---

## Filenames (NEW)
* [ ] yt-dlp output template `%(title)s [%(id)s].%(ext)s` (not bare `%(id)s`) so the editor bin shows real names instead of cryptic IDs. `[id]` suffix keeps cache-key uniqueness. Truncate long titles; `--restrict-filenames` sanitizes.

---

## Pre-flight validation
* [ ] A standalone validator that checks a yaml WITHOUT spending credits/downloads with whatever is sensitive to data/credit usage
    * Checks: voice IDs exist in the ElevenLabs library, YouTube via `yt-dlp --simulate` (plain HTTP HEAD always 403s), other URLs with a browser UA, timestamps well-formed, local assets present, truncated YT IDs, stem names. Report ALL problems at once.
    * [ ] Fold `vvv_preflight.py` in as `vvv check <script>`; when `--target hyperframes`, also check node >= 22 + hyperframes resolvable.

---

## DSL extensibility (decouple nodes/parser like producers)
* [x] Adding a directive currently requires editing CORE files (`ir/nodes.py` + `phases/ parse.py`). Garbage. Done for the parse half: you add `node.py` + `directive.py` in your plugin package, and neither file changes.
    * A directive should be a self-contained plugin = node + parse-handler (registered by key) + producer, all from outside core.
    * [x] Build a parse-handler registry (key => fn, dispatched in `_parse_entry` the way
  producers dispatch by node_type). `register_directive(Directive(name, aliases, parse, keys))`, stored in `registry.DIRECTIVES`; `keys` = entry-level keys the directive reads, so parse can warn on unknown keys and error on keys two directives in one entry both read.
    * [ ] Then directives plug in via entry points like stem backends do. Not yet: your plugin only registers if `vvv.plugins` imports its package.
    * [ ] Still core-coupled for a new directive: composition.py wiring (`build(config)` below), the `MediaKind` literal in `ir/resolved.py`, and the assembler's kind dispatch (the kdencli assembler also imports `ClipNode` directly).
    * Just copy the producer/backend registration pattern to be honest. That's literally it
    * **Update - it's only half that simple.** Registries work when constructors take no args (sources, stem backends). Producers need injected deps (`NarrateProducer(tts)`, `StemProducer(separator)`), so `@register_producer` is decoration only - read by `--list-producers`, not by resolve.
        * Node (dataclass) and parse handler (`(value, entry) -> Node`) really can copy the source pattern. Done - the handler is `(value, entry, matched_key) -> Node`, nodes subclass `ir/nodes.Node`.
        * Producer: register a factory, `@classmethod build(cls, config)`; composition.py becomes `{n: cls.build(config) for n, cls in PRODUCERS.items()}`. Context still never carries backends.
        * Needs a `Config` object, not the full config layer: a frozen dataclass filled from today's env vars is enough.
        * First real consumer is the assembler registry (`--target kdenlive|hyperframes`). Land `build(config)` for assemblers + producers together then.
        * [x] Now: add the missing `@register_producer` to Stem + Title so `--list-producers` stops lying.
        * Producers are stateful per run (`NarrateProducer._counter`): build fresh each run, never cache instances.
        * Replace import-side-effect registration (`import vvv.plugins` in cli.py) with explicit entry-point loading.

---

## New media sources: gen AI + programmatic - OPEN, be careful
No new "Generator" abstraction. Everything that produces media is already a generator (yt-dlp, ElevenLabs, x-minus, titles). The pattern already exists: directive (intent) -> Producer (resolve to a file) -> swappable backend. Gen AI is just more backends/directives in that pattern. A `Generator` ABC + `gen:` directive would be a category-by-technology abstraction duplicating Producer. Dropped.
* The only things that are actually new (and might need core changes):
    * [ ] Nondeterministic producers need PINNING (see Caching). Not new either: ElevenLabs already gives a different take every call, the counter cache just pins it by accident. A producer property + lock file, not a class hierarchy.
    * [ ] Some outputs need a human ACCEPT before they get pinned (agent edits, image/video gen). A review step, not a type.
    * [ ] New media kind: HTML sub-composition (diagrams, agent edits). HyperFrames places it natively; kdencli would need it pre-rendered to mp4 (`hyperframes render`). Assembler capability question.
* How things could slot in (candidates, not decided):
    * New TTS (e.g. Fish drama-3) = another `TTSBackend`.
    * Image/video from a prompt = the existing `i:`/`v:` with `prompt:` instead of a source, resolved by a backend (or a SourceHandler: resolve is already "turn intent into a file").
    * Programmatic visual descriptions directly in the script (archify JSON spec, Mermaid) = a directive whose producer runs a deterministic renderer. Zero AI.
    * Natural-language `e:` edits/animations, two modes:
        * routed: `via: <backend>` pipes straight to a specific model/tool. Predictable, cheap. Default.
        * delegated: the agent gets the available backends as tools and can combine them. Probabilistic, expensive, opt-in. Output still goes through accept + pin.
    * Remembering types of edits/animations: presets first (accepted artifacts, parameterized, zero tokens). A skill (prose for an agent) only for "make a new one in this style", and only after 3+ similar accepted edits.
```yaml
# candidate shapes only
- i: { prompt: "...", via: qwen-image, seed: 42 }   # image from a prompt
- diagram: { via: archify, spec: {...} }            # programmatic, zero tokens
- e: "big head shake on the punchline"
  via: agent                                        # delegated, opt-in
```
* [ ] LLM ladder - only climb as far as needed: hand-written spec (0 tokens) -> template + your values (0 tokens) -> LLM fills a small spec (cheap, can be local/offline) -> agent free-form (expensive).
* [ ] Skills are mostly "LLM writes HTML/SVG/JSON" over a deterministic renderer. Call the renderer directly, skip the skill:
    * archify: agent writes typed JSON IR, zero-dep Node CLI validates/renders. vvv can emit the IR itself.
    * diagram-design: HTML/SVG templates + imports Mermaid/Excalidraw/draw.io + `self_check.py`. Feed it Mermaid.
    * anatomy: plain JS/SVG/WebGL `kit/`, but the agent invents the object, so it's the expensive one.
    * All output HTML => drop straight into HyperFrames as sub-compositions.
* [ ] Offline rule: rendering + caching must work offline; generation may need the network (same as acquisition).
* [ ] Reality check per backend before wiring it:
    * No strong GPU here => local = small models only; big ones = hosted API or rented GPU (RunPod/Modal), both cost money + network.
    * Google Flow has no API. Use Veo via the Gemini API (billed separately from Flow / AI Pro).
    * Wan: 2.2 is open (Apache 2.0, 5B needs 24 GB VRAM); 2.5 -> 3.0 are API-only.
    * MiniMax H3: 15 s / 2K video with audio, weights "coming", check status.
    * Qwen-Image-2.1 = Qwen Research License, Fish drama-3 = Fish Community License: check commercial use for a monetized channel.
    * YouTube requires disclosure for realistic synthetic content, especially of real people. No fake artists.

---

## Config layer
* [ ] ElevenLabs voice + stem backend are hardcoded/env-var. Need real config.
    * Per-project (meta in YAML) + global config file.
        * Started: a top-level `config:` block in the script (`vvv/config.py`). Each component reads its own section via `from_config` (`narrate.adopt_legacy`, `elevenlabs.model_id`), so composition.py never learns a section's keys. Unknown keys/sections warn. Global file not yet.
    * Backend selection (stem, TTS), API keys, kdencli path, default fonts/tracks.
    * composition.py reads config instead of hardcoding shit.
    * Also: assembler target, hyperframes path, new media backends + their API keys.

---

## Narration voice style
* [ ] Bake speed 1.2x / pitch 0.85 into the narration audio at produce time with ffmpeg (`rubberband=tempo=1.2:pitch=0.85`, or `atempo` + `asetrate`), cached under the same key + style params. Works for every backend; no editor-side effect. Check `ffmpeg -filters | grep rubberband` first.
* [ ] Per-line override in DSL (`style:` on narrate, default in meta).

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
* [ ] Prereq: youtube handler (now `plugins/sources/ytdlp`, all yt-dlp sites) forwards title/date/uploader into `info.meta`.
* Not the same as HyperFrames variables: vvv vars resolve at compile time; HF variables are render-time parameters for preset/agent compositions.

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
* If it happens at the DSL level: only as an expand-time generator that emits plain YAML (`vvv expand`), never evaluated at render time. Lua as a kdencli execution layer is a separate idea in `KDENCLI_TODO.md`.

---

## Probe consolidation (BANK)
* [ ] Consolidate the à-la-carte probe fns (has_audio_stream / has_video_stream / probe_duration / ...) into one `probe(path) -> MediaInfo{has_video, has_audio, duration, is_image}`. One ffprobe call, one struct; kills scattered imports + triple-probe waste. (The image-duration and audio-routing bugs both came from these being separate.)

---

## TextMetrics cross-platform
* [ ] Currently fontconfig (fc-match) on Linux + FreeType. Only estimates for Mac/Windows.
* [ ] `--font-file` override (FreeType is cross-platform; bypasses fc-match).
* [ ] Later: CoreText (Mac) / DirectWrite (Windows) resolvers
* kdencli-side only; the HyperFrames backend doesn't need it (the browser does text layout).

---

## Stem backend completion
* [ ] Finish `LocalDemucs.separate()` (the public reference backend is still a STUB, mostly because I can't test LocalDemucs as I do not have a powerful GPU, so far only stem backend tested is an unexposed script using that bots some online platform that offers stem separation)
    * No GPU isn't a blocker for *testing*: htdemucs runs on CPU, and stems are separated on the trimmed segment, so a 10-30 s clip takes minutes. Run it once on a short trim.
    * [ ] When you implement it: use `sys.executable`, not `"python3"`; `--two-stems vocals` when only vocals are requested.
    * [x] StemProducer uses the shared `media.trim`.

---

## Pronunciation layer (BANK)
* [ ] Separate canonical text from TTS-spelling. Currently phonetic hacks are inline in the script, which corrupts the text for any non-audio use (captions, display). Build a pron-map (canonical => TTS-spelling / SSML / phonemes) applied ONLY at the narrate/TTS step. Keeps source text canonical, fixes pronunciation.
    * Priority up: generated captions need canonical text ("Vybz Kartel", not "Vibes Kartel").

---

## Producer / media correctness (verify, some may already be fixed)
* [x] `keep_audio`: string branch of `_parse_clip` never sets it -> it stays True, so `audio: false` is silently ignored. Fixed: `audio:` is read for every clip.
* [x] Clip parser footgun: string branch returns before reading entry-level `from:`/`to:`/`audio:`. Same in _parse_stem. The non-string branch (the only one reading them) is effectively unreachable. Fixed: both go through `util/dsl.split_source_range`; inline range + `from:`/`to:` together is an error.
* [x] `download_image_media` sends a browser User-Agent.
* [x] Parser: unknown keys must warn, not be silently dropped (`t:` is still dropped - not in KEYS["title"]). Fixed: `t:` is a title alias; unknown keys and entries without a directive warn, conflicts and bad values error (all reported at once).
* [ ] Parser: when a script has errors, its warnings aren't printed - print both together.
* [ ] `v:`/`i:` accept a source string only; the dict form (`i: { prompt: ... }` from New media sources) errors for now.

---

## KdenCLI
C++-side work lives in the KdenCLI repo's own `KDENCLI_TODO.md`.

---

## Dropped / superseded
* MPV interactive preview (old V4) -> HF preview + Studio for the HF backend. Revisit only if a terminal "pause at gaps, re-prompt" loop is still wanted.
* OTIO second assembler -> parked indefinitely.

---

## Misc banked
* [ ] Fractional fps / float drift -> integer frames (both backends). Sub-second timestamps already parse (`1:05.5`) and reach kdencli as `M:SS.mmm`.
* [ ] Blog post - after a video actually ships.
