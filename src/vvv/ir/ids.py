"""Deterministic element IDs for assemblers that need stable references (HyperFrames overrides,
agent sub-compositions). Position-independent: built from the node's content, so moving a line
keeps its ID. Identical nodes are told apart by an occurrence index (-1, -2, ...).
"""
from __future__ import annotations
import dataclasses

from vvv.ir.nodes import Node
from vvv.util.cache import cache_key


def node_key(node: Node) -> str:
    return cache_key("node", type=type(node).__name__, fields=dataclasses.asdict(node))


def element_ids(nodes: list[Node]) -> list[str]:
    """One ID per node, e.g. 'narrate-3f9a1c2b7d4e-1'. Stable under reordering and edits to OTHER nodes."""
    seen: dict[str, int] = {}
    ids = []
    for node in nodes:
        key = node_key(node)
        seen[key] = seen.get(key, 0) + 1
        kind = type(node).__name__.removesuffix("Node").lower()
        ids.append(f"{kind}-{key[:12]}-{seen[key]}")
    return ids
