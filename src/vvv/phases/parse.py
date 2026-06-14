from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any
import os

import yaml

from vvv.ir.nodes import Node, NarrateNode, ClipNode, PauseNode, StemNode, TitleNode, TitleStyle
from vvv.context import Meta



KEYS = {
    "narrate":  ("n", "narrate"),
    # Technically, an image is just a clip with a duration
    "clip":     ("v", "clip", "i", "image"),
    "pause":    ("_", "pause"),
    "stem":     ("stem",),
    "title": ("title", "text"),
}

META_KEYS = {
    "title":      "title",
    "voice_id":   "voice",
    "fps":        "fps",
    "resolution": "res",
    "assets_dir": "assets_dir",
    "char_lim":   "char_lim",
    "script":     "s",
}


_TIMESTAMP_RANGE = re.compile(
    r"""
    \s*
    \[                                      # opening bracket
    (\d{1,2}(?::\d{2}){1,2})                # group 1: start, M:SS or H:MM:SS
    -                                       # separator (":")
    (\d{1,2}(?::\d{2}){1,2})                # group 2: end, same
    \]                                      # closing bracket
    $
    """,
    re.VERBOSE,
)

@dataclass(frozen=True, slots=True)
class ParsedScript:
    meta: Meta
    nodes: list[Node]


def parse(raw: dict) -> ParsedScript:
    meta = _parse_meta(raw.get("meta", {}))
    nodes: list[Node] = []
    for entry in raw.get(META_KEYS["script"], []):
        nodes.extend(_parse_entry(entry))
    return ParsedScript(meta=meta, nodes=nodes)


def _parse_meta(raw: dict) -> Meta:
    return Meta(
        title=raw.get(META_KEYS["title"], "untitled"),
        voice_id=raw.get(META_KEYS["voice_id"], ""),
        fps=raw.get(META_KEYS["fps"], 30),
        resolution=tuple(raw.get(META_KEYS["resolution"], [1920, 1080])),
        assets_dir=Path(raw.get(META_KEYS["assets_dir"], "assets/")),
        char_lim=raw.get(META_KEYS["char_lim"], 5000),
    )


def _has(entry: dict, directive: str) -> str | None:
    for k in KEYS[directive]:
        if k in entry:
            return k
    return None


def _parse_entry(entry: dict) -> list[Node]:
    nodes: list[Node] = []

    if k := _has(entry, "narrate"):
        nodes.append(NarrateNode(text=str(entry[k])))

    if k := _has(entry, "clip"):
        nodes.append(_parse_clip(entry[k], entry, matched_key=k))

    if k := _has(entry, "pause"):
        nodes.append(PauseNode(duration_s=float(entry[k])))

    if k := _has(entry, "stem"):
        nodes.append(_parse_stem(entry[k], entry))
    

    #TODO : Implement image, edit, text_overlay, etc...
    return nodes


def _parse_clip(value: Any, entry: dict, matched_key: str) -> ClipNode:
    audio = entry.get("audio", True)
    if matched_key in ("i", "image"):
        return ClipNode(
            source=str(value).strip(),
            duration_s=float(entry["d"]) if "d" in entry else 1.0,
        )
    
    if isinstance(value, str):
        ts = _TIMESTAMP_RANGE.search(value)
        if ts:
            return ClipNode(
                source=value[:ts.start()].strip(),
                from_s=_parse_timestamp(ts.group(1)),
                to_s=_parse_timestamp(ts.group(2)),
            )
        return ClipNode(source=value.strip())
    return ClipNode(
        source=str(value),
        from_s=_parse_timestamp(entry["from"]) if "from" in entry else None,
        to_s=_parse_timestamp(entry["to"]) if "to" in entry else None,
        keep_audio=audio
    )


def _parse_timestamp(ts: str) -> float:
    # '1:05' -> 65.0, '1:02:03' -> 3723.0, '12' -> 12.0
    parts = [int(p) for p in str(ts).strip().split(":")]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return float(seconds)

def _parse_stem(value: Any, entry: dict) -> "StemNode":
    stems = tuple(entry.get("stems", ["vocals"]))

    if isinstance(value, str):
        ts = _TIMESTAMP_RANGE.search(value)
        if ts:
            return StemNode(
                source=value[:ts.start()].strip(),
                stems=stems,
                from_s=_parse_timestamp(ts.group(1)),
                to_s=_parse_timestamp(ts.group(2)),
            )
        return StemNode(source=value.strip(), stems=stems)

    return StemNode(
        source=str(value),
        stems=stems,
        from_s=_parse_timestamp(entry["from"]) if "from" in entry else None,
        to_s=_parse_timestamp(entry["to"]) if "to" in entry else None,
    )