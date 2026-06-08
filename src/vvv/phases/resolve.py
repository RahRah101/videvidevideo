from __future__ import annotations

from vvv.ir.resolved import ResolvedEntry
from vvv.ir.nodes import Node
from vvv.context import Context
from vvv.interfaces.producer import Producer

def resolve(nodes: list[Node],
            producers: dict[type, Producer],
            ctx: Context) -> list[ResolvedEntry]:
    out: list[ResolvedEntry] = []
    for node in nodes:
        producer = producers.get(type(node))
        if producer is None:
            raise RuntimeError(f"no producer for {type(node).__name__}")
        out.append(producer.produce(node, ctx))
    return out


