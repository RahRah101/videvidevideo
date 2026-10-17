from __future__ import annotations
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from vvv.util.dsl import split_source_range
from .node import StemNode


def _parse_stem(value: Any, entry: dict, matched_key: str) -> StemNode:
    stems = entry.get("stems", ["vocals"])
    if isinstance(stems, str):          # stems: vocals
        stems = [stems]
    if not stems or not all(isinstance(s, str) for s in stems):
        raise ValueError(f"stems: must be a stem name or a list of names, got {stems!r}")

    source, from_s, to_s = split_source_range(value, entry)
    return StemNode(source=source, stems=tuple(stems), from_s=from_s, to_s=to_s)


register_directive(Directive("stem", ("stem",), _parse_stem, frozenset({"stems", "from", "to"})))
