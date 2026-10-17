from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

from vvv.ir.nodes import Node
from vvv.context import Meta
from vvv.registry import DIRECTIVES


META_KEYS = {
    "title":      "title",
    "voice_id":   "voice",
    "fps":        "fps",
    "resolution": "res",
    "assets_dir": "assets_dir",
    "char_lim":   "char_lim",
    "script":     "s",
}


@dataclass(frozen=True, slots=True)
class ParsedScript:
    meta: Meta
    nodes: list[Node]


def parse(raw: dict) -> ParsedScript:
    if not DIRECTIVES:
        raise RuntimeError("no directives registered - import vvv.plugins before parsing")
    meta = _parse_meta(raw.get("meta", {}))
    nodes: list[Node] = []
    for entry in raw.get(META_KEYS["script"], []):
        nodes.extend(_parse_entry(entry))
    return ParsedScript(meta=meta, nodes=nodes)


def _parse_meta(raw: dict) -> Meta:
    return Meta(
        title=raw.get(META_KEYS["title"], "untitled"),
        voice_id=raw.get(META_KEYS["voice_id"]) or os.environ.get("ELEVENLABS_VOICE_ID", ""),
        fps=raw.get(META_KEYS["fps"], 30),
        resolution=tuple(raw.get(META_KEYS["resolution"], [1920, 1080])),
        assets_dir=Path(raw.get(META_KEYS["assets_dir"], "assets/")),
        char_lim=raw.get(META_KEYS["char_lim"], 5000),
    )


def _parse_entry(entry: dict) -> list[Node]:
    # One entry can yield several nodes, in the order their keys appear in the entry.
    # Each directive (plugins/producers/*/directive.py) parses its own value + entry-level keys.
    nodes: list[Node] = []
    seen = set()
    for key, value in entry.items():
        directive = DIRECTIVES.get(key)
        if directive is None or directive.name in seen:
            continue
        seen.add(directive.name)
        nodes.append(directive.parse(value, entry, key))
    return nodes
