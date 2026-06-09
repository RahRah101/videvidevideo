from __future__ import annotations
from pathlib import Path

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from vvv.ir.nodes import Node, ClipNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context
from vvv.util.media import resolve_media, probe_duration, has_audio_stream

@register_producer
class ClipProducer(Producer):
    node_type = ClipNode

    def produce(self, node: Node, ctx: Context) -> ResolvedEntry:
        assert isinstance(node, ClipNode)
        local_path = resolve_media(
            node.source,
            ctx.meta.assets_dir,
            ctx.work_dir / "media",
        )
        file_has_audio = has_audio_stream(local_path)
        effective_audio = node.keep_audio and file_has_audio

        return ResolvedEntry(
            node=node,
            media=Path(local_path),
            kind="video",
            duration_s=probe_duration(local_path),
            extras={"has_audio": effective_audio},
        )