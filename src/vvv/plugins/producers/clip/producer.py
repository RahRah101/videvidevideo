from __future__ import annotations
from pathlib import Path

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from vvv.ir.nodes import Node, ClipNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context
#TODO: This is fcking garbage. four separate media-probing functions imported à la carte. Turn that into one probe thing later.
from vvv.util.media import resolve_media, probe_duration, has_audio_stream, has_video_stream

@register_producer
class ClipProducer(Producer):
    node_type = ClipNode

    def produce(self, node: Node, ctx: Context) -> ResolvedEntry:
        assert isinstance(node, ClipNode)

        info = resolve_media(node.source, ctx)
        has_video = has_video_stream(info.path)
        
        kind = "video"
        if node.duration_s is not None: 
            kind = "image"
        else:
            kind = "video" if has_video else "audio"

        return ResolvedEntry(
            node=node,
            media=info.path,
            kind = kind,
            duration_s=node.duration_s if node.duration_s is not None else probe_duration(info.path),
            extras={
                "has_audio": node.keep_audio and has_audio_stream(info.path),
                # everything the source discovered
                **info.meta,
            },
        )
