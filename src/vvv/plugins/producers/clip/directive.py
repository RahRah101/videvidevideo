from __future__ import annotations
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from vvv.util.dsl import pick, split_source_range
from .node import ClipNode


def _parse_clip(value: Any, entry: dict, matched_key: str) -> ClipNode:
    source, from_s, to_s = split_source_range(value, entry)
    audio = entry.get("audio", True)
    if not isinstance(audio, bool):
        raise ValueError(f"audio: must be true or false, got {audio!r}")
    return ClipNode(source=source, from_s=from_s, to_s=to_s, keep_audio=audio)


def _parse_image(value: Any, entry: dict, matched_key: str) -> ClipNode:
    if isinstance(value, (dict, list)):
        raise ValueError(f"expected a source string, got a {type(value).__name__}")
    return ClipNode(
        source=str(value).strip(),
        duration_s=float(pick(entry, "duration", "d", default=1.0)),
    )


# Technically, an image is just a clip with a duration.
# Two directives (not one) because they read different entry keys.
register_directive(Directive("clip", ("v", "clip"), _parse_clip, frozenset({"from", "to", "audio"})))
register_directive(Directive("image", ("i", "image"), _parse_image, frozenset({"d", "duration"})))
