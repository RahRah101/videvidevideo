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

        info = resolve_media(node.source, ctx)

        return ResolvedEntry(
            node=node,
            media=info.path,
            kind="video",
            duration_s=probe_duration(info.path),
            extras={
                "has_audio": node.keep_audio and has_audio_stream(info.path),
                # everything the source discovered
                **info.meta,
            },
        )
