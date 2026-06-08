from __future__ import annotations
from pathlib import Path

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from vvv.ir.nodes import Node, NarrateNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context
from vvv.util.media import probe_duration
from .tts_backend import TTSBackend


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
        out = audio_dir / f"narrate_{self._counter:03d}.mp3"

        self.tts.synthesize(node.text, ctx.meta.voice_id, out)

        return ResolvedEntry(
            node=node,
            media=out,
            kind="audio",
            duration_s=probe_duration(out),
        )
