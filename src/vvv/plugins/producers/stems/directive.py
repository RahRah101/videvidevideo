from __future__ import annotations
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from vvv.util.timestamps import TIMESTAMP_RANGE, parse_timestamp
from .node import StemNode


def _parse_stem(value: Any, entry: dict, matched_key: str) -> StemNode:
    stems = tuple(entry.get("stems", ["vocals"]))

    if isinstance(value, str):
        ts = TIMESTAMP_RANGE.search(value)
        if ts:
            return StemNode(
                source=value[:ts.start()].strip(),
                stems=stems,
                from_s=parse_timestamp(ts.group(1)),
                to_s=parse_timestamp(ts.group(2)),
            )
        return StemNode(source=value.strip(), stems=stems)

    return StemNode(
        source=str(value),
        stems=stems,
        from_s=parse_timestamp(entry["from"]) if "from" in entry else None,
        to_s=parse_timestamp(entry["to"]) if "to" in entry else None,
    )


register_directive(Directive("stem", ("stem",), _parse_stem))
