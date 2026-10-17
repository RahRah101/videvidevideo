from __future__ import annotations
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from vvv.util.timestamps import TIMESTAMP_RANGE, parse_timestamp
from .node import ClipNode


def _parse_clip(value: Any, entry: dict, matched_key: str) -> ClipNode:
    audio = entry.get("audio", True)
    if matched_key in ("i", "image"):
        return ClipNode(
            source=str(value).strip(),
            duration_s=float(entry["d"]) if "d" in entry else 1.0,
        )

    if isinstance(value, str):
        ts = TIMESTAMP_RANGE.search(value)
        if ts:
            return ClipNode(
                source=value[:ts.start()].strip(),
                from_s=parse_timestamp(ts.group(1)),
                to_s=parse_timestamp(ts.group(2)),
            )
        return ClipNode(source=value.strip())
    return ClipNode(
        source=str(value),
        from_s=parse_timestamp(entry["from"]) if "from" in entry else None,
        to_s=parse_timestamp(entry["to"]) if "to" in entry else None,
        keep_audio=audio
    )


# Technically, an image is just a clip with a duration
register_directive(Directive("clip", ("v", "clip", "i", "image"), _parse_clip))
