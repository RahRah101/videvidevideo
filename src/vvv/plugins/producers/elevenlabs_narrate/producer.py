from __future__ import annotations
from pathlib import Path

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from vvv.ir.nodes import Node, NarrateNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context
from vvv.util.media import probe_duration
from .tts_backend import TTSBackend

from vvv.util.text import split_for_tts
from vvv.util.media import probe_duration, concat
import hashlib

@register_producer
class NarrateProducer(Producer):
    node_type = NarrateNode

    def __init__(self, tts: TTSBackend):
        self.tts = tts
        #this is just to name the files later
        self._counter = 0

    def produce(self, node: Node, ctx: Context) -> ResolvedEntry:
        assert isinstance(node, NarrateNode)
        self._counter += 1
        audio_dir = ctx.work_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        voice = node.voice or ctx.meta.voice_id

        chunks = split_for_tts(node.text, ctx.meta.char_lim)
        #TODO:Uncomment this
        #key = hashlib.sha256(f"{text}\x00{voice}".encode()).hexdigest()[:16]
        #out = audio_dir / f"narrate_{key}.mp3"
        #TODO:Comment this 
        out = (audio_dir / f"narrate_{self._counter:03d}.mp3").resolve()



        # Crude caching that assumes re-runs on the same yaml... this is just to help me save credits when testing on a big script so I don't send requests to ElevenLabs again and again
        #TODO : Better caching behavior. Use text+voice_id prolly.
        if out.exists():
            return ResolvedEntry(
                node=node,
                media=out,
                kind="audio",
                duration_s=probe_duration(out),
            )

        if len(chunks) == 1:
            self.tts.synthesize(chunks[0], voice, out)
        else:
            parts = []
            for i, chunk in enumerate(chunks):
                part = (audio_dir / f"narrate_{self._counter:03d}_{i:03d}.mp3").resolve()
                self.tts.synthesize(chunk, voice, part)
                parts.append(part)
            concat(parts, out)
        
        return ResolvedEntry(
            node=node,
            media=out,
            kind="audio",
            duration_s=probe_duration(out),
        )
