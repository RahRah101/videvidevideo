## Track model: 
- kill the hardcoded VIDEO/TTS/AUDIO_TRACK in the assembler. This shit is dumb as hell.
- Default = auto-allocate by kind (kdencli has FindOrCreateTrack)
- Explicit = track: <name> in DSL

## DSL extensibility (decouple nodes/parser like producers)
- So I just noticed I have to edit CORE FILES (ir/nodes and phases/parse.py) EVERYTIME I had a new directive. This is garbage. Adding a directive shouldn't require editing ir/nodes.py + parse.py.
- A directive should be a self-contained plugin = node + parse-handler
  (registered by key) + producer, all from outside core.
- Build a parse-handler registry (key -> fn, dispatched in _parse_entry the way producers dispatch by node_type) + open the Node union.
- Then directives plug in via entry points like stem backends(that I started to write) do
- The producer/backend registration pattern already gives you a blueprint 

## Config layer
- ElevenLabs + stem backend are hardcoded/env-var. Need real config.
- Per-project (meta in YAML) + global config file 
- Backend selection (stem, TTS), API keys, kdencli path, default fonts/tracks.
- composition.py reads config instead of hardcoding shit 

## User-defined snippets (DSL macros)
- A `defs:` block in the USER's YAML (mechanism in vvv,
snips are user policy).
- Parse reads `defs` into a runtime macro table.
- `use: name args: {...}` expands snip body (substitute params); body entries recurse through _parse_entry (snips compose).
- e.g. copyright_snip(title, author) -> generate bottom-center author AND top-left title.

## Variable binding / metadata threading
- Static vars: parse-time env + substitution.
- Dynamic source-metadata: `bind: {title: meta.title}` -> Ref(name) placeholder in IR nodes -> resolved in resolve-phase from forwarded extras (the extras forwarding is the substrate). Node text becomes str | Ref.
- e.g Threads source title/author into copyright snips (see above) automatically.

## TextMetrics cross-platform
Currently fontconfig (fc-match) on Linux + FreeType. Nothing but estimates for Mac/Windows
- `--font-file` override (FreeType is cross-platform; bypasses fc-match)
- Later write some CoreText (Mac) / DirectWrite (Windows) resolvers

## SourceHandler range support (acquisition trim)
yt-dlp downloads full then trims, which is wasteful. If I was still in Africa I would have fixed that already to save my poor mobile data.
- `--download-sections` for acquisition-trim (legit fetch concern).
- Chicken-and-egg: range split across node[from-to] + ?t= start_hint. TODO in the handler 

## Stem backend completion
- Finish LocalDemucs.separate()
