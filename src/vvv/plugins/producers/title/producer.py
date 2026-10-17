from __future__ import annotations

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from .node import TitleNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context


@register_producer
class TitleProducer(Producer):
    node_type = TitleNode

    def produce(self, node: TitleNode, ctx: Context) -> ResolvedEntry:
        return ResolvedEntry(
            node=node,
            media=None,
            kind="title",
            duration_s=node.duration_s,
            extras={}
        )