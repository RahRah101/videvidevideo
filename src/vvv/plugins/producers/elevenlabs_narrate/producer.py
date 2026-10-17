from __future__ import annotations
from pathlib import Path
import re

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from vvv.ir.nodes import Node
from .node import NarrateNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context
from .tts_backend import TTSBackend

from vvv.util.text import split_for_tts
from vvv.util.media import probe_duration, concat
from vvv.util.cache import Cache, cache_key
from vvv.plugin_loader import backend_names, load_backend

# Pre-content-hash cache files: narrate_001.mp3 (keyed on position only)
_LEGACY_NAME = re.compile(r"narrate_(\d{3})\.mp3")


@register_producer
class NarrateProducer(Producer):
    node_type = NarrateNode
    CONFIG_SECTION = "narrate"
    CONFIG_KEYS = {"tts", "adopt_legacy"}
    TTS_GROUP = "vvv.tts_backends"      # entry-point group; `tts:` picks one by name
    DEFAULT_TTS = "elevenlabs"

    @classmethod
    def build(cls, config) -> "NarrateProducer":
        section = config.section(cls.CONFIG_SECTION, cls.CONFIG_KEYS)
        adopt = section.get("adopt_legacy", False)
        if not isinstance(adopt, bool):
            raise ValueError(f"config.narrate.adopt_legacy: must be true or false, got {adopt!r}")
        tts_cls = load_backend(cls.TTS_GROUP, str(section.get("tts", cls.DEFAULT_TTS)))
        return cls(tts_cls.from_config(config), adopt_legacy=adopt)

    @classmethod
    def config_sections(cls) -> set[str]:
        # each TTS backend reads a section named after its entry point (e.g. `elevenlabs:`)
        return {cls.CONFIG_SECTION, *backend_names(cls.TTS_GROUP)}

    def __init__(self, tts: TTSBackend, adopt_legacy: bool = False):
        self.tts = tts
        # adopt_legacy: rename old narrate_NNN.mp3 files to their content key instead of
        # paying ElevenLabs again. Assumes the script hasn't changed since they were made.
        self.adopt_legacy = adopt_legacy
        #this is just to name the files later (human ordering). Cache identity is the content key.
        self._counter = 0

    def produce(self, node: Node, ctx: Context) -> ResolvedEntry:
        assert isinstance(node, NarrateNode)
        self._counter += 1
        audio_dir = ctx.work_dir / "audio"
        cache = Cache(audio_dir)
        if self._counter == 1:
            self._check_legacy(audio_dir)

        voice = node.voice or ctx.meta.voice_id
        prefix = f"narrate_{self._counter:03d}"
        chunks = split_for_tts(node.text, ctx.meta.char_lim)
        identity = self.tts.cache_identity()
        chunk_keys = [cache_key("narrate_chunk", text=c, voice=voice, **identity) for c in chunks]
        # one chunk: the chunk IS the narration. Several: the result is keyed by its parts.
        key = chunk_keys[0] if len(chunk_keys) == 1 else cache_key("narrate", parts=chunk_keys)

        if cache.find(key, ".mp3") is None and self.adopt_legacy:
            self._adopt(audio_dir, cache, key, prefix)

        def synth_chunk(chunk: str):
            return lambda tmp: self.tts.synthesize(chunk, voice, tmp)

        def make(tmp: Path):
            # each chunk is its own cache entry, so a run that dies midway only redoes what's missing
            parts = [
                cache.get_or_make(k, synth_chunk(c), prefix=f"{prefix}_part{i:03d}", suffix=".mp3")
                for i, (c, k) in enumerate(zip(chunks, chunk_keys))
            ]
            concat(parts, tmp)

        if len(chunks) == 1:
            out = cache.get_or_make(key, synth_chunk(chunks[0]), prefix=prefix, suffix=".mp3")
        else:
            out = cache.get_or_make(key, make, prefix=prefix, suffix=".mp3")

        return ResolvedEntry(
            node=node,
            media=out,
            kind="audio",
            duration_s=probe_duration(out),
        )

    def _check_legacy(self, audio_dir: Path) -> None:
        # Old files can't be matched to their text. Without adoption the run would quietly
        # re-narrate (and pay for) everything, so stop and make it a choice.
        if self.adopt_legacy or not audio_dir.is_dir():
            return
        legacy = sorted(p.name for p in audio_dir.iterdir() if _LEGACY_NAME.fullmatch(p.name))
        if legacy:
            raise RuntimeError(
                f"{len(legacy)} old-style narration file(s) in {audio_dir} ({legacy[0]}, ...).\n"
                "  Reuse them (assumes the script hasn't changed since): add to the script, run once, then remove:\n"
                "      config:\n"
                "        narrate: { adopt_legacy: true }\n"
                "  Or delete them to pay for fresh takes."
            )

    def _adopt(self, audio_dir: Path, cache: Cache, key: str, prefix: str) -> None:
        legacy = audio_dir / f"{prefix}.mp3"
        if legacy.exists():
            target = cache.path_for(key, prefix, ".mp3")
            legacy.rename(target)
            print(f"[narrate] adopted {legacy.name} -> {target.name}")
