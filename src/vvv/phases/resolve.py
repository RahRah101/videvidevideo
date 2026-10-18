from __future__ import annotations
from dataclasses import replace

from vvv.ir.resolved import ResolvedEntry
from vvv.ir.placement import Placement
from vvv.ir.nodes import Node
from vvv.context import Context
from vvv.interfaces.producer import Producer

def resolve(nodes: list[Node],
            producers: dict[type, Producer],
            ctx: Context,
            placements: list[Placement] | None = None) -> list[ResolvedEntry]:
    # placements runs parallel to nodes (ParsedScript.placements); None = all default
    placements = placements or [Placement()] * len(nodes)
    out: list[ResolvedEntry] = []
    for node, placement in zip(nodes, placements, strict=True):
        producer = producers.get(type(node))
        if producer is None:
            raise RuntimeError(f"no producer for {type(node).__name__}")
        out.append(replace(producer.produce(node, ctx), placement=placement))
    return out


