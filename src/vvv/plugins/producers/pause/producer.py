from __future__ import annotations

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from vvv.ir.nodes import Node, PauseNode
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context


@register_producer
class PauseProducer(Producer):
    directive = "pause"

    def produce(self, node: Node, ctx: Context) -> ResolvedEntry:
        assert isinstance(node, PauseNode)
        return ResolvedEntry(
            node=node,
            media=None,
            kind="marker",
            duration_s=node.duration_s,
        )
