from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os

from vvv.ir.nodes import Node
from vvv.context import Meta
from vvv.registry import DIRECTIVES
from vvv.util.dsl import pick


# canonical name -> accepted YAML keys (shorthand first)
META_KEYS = {
    "title":      ("title",),
    "voice_id":   ("voice", "voice_id"),
    "fps":        ("fps",),
    "resolution": ("res", "resolution"),
    "assets_dir": ("assets_dir",),
    "char_lim":   ("char_lim",),
}
SCRIPT_KEYS = ("s", "script")


class DSLError(ValueError):
    """Every error found in the script, one per line."""


@dataclass(frozen=True, slots=True)
class ParsedScript:
    meta: Meta
    nodes: list[Node]
    # unknown keys / entries without a directive: ignored, but never silently
    warnings: list[str] = field(default_factory=list)


def parse(raw: dict) -> ParsedScript:
    if not DIRECTIVES:
        raise RuntimeError("no directives registered - import vvv.plugins before parsing")
    raw = raw or {}
    errors: list[str] = []
    warnings: list[str] = []

    for key in raw:
        if key != "meta" and key not in SCRIPT_KEYS:
            warnings.append(f"top level: unknown key {key!r} ignored")

    meta = None
    try:
        meta = _parse_meta(raw.get("meta") or {}, warnings)
    except (ValueError, TypeError) as e:
        errors.append(f"meta: {e}")

    nodes: list[Node] = []
    try:
        script = pick(raw, *SCRIPT_KEYS, default=[]) or []
    except ValueError as e:
        errors.append(f"top level: {e}")
        script = []

    for i, entry in enumerate(script, start=1):
        where = f"entry {i} ({_label(entry)})"
        try:
            entry_nodes, entry_warnings = _parse_entry(entry)
        except (ValueError, TypeError) as e:
            errors.append(f"{where}: {e}")
            continue
        nodes.extend(entry_nodes)
        warnings.extend(f"{where}: {w}" for w in entry_warnings)

    if errors:
        raise DSLError("\n".join(errors))
    return ParsedScript(meta=meta, nodes=nodes, warnings=warnings)


def _parse_meta(raw: dict, warnings: list[str]) -> Meta:
    known = {k for aliases in META_KEYS.values() for k in aliases}
    for key in raw:
        if key not in known:
            warnings.append(f"meta: unknown key {key!r} ignored")

    def get(name, default=None):
        return pick(raw, *META_KEYS[name], default=default)

    return Meta(
        title=get("title", "untitled"),
        voice_id=get("voice_id") or os.environ.get("ELEVENLABS_VOICE_ID", ""),
        fps=get("fps", 30),
        resolution=tuple(get("resolution", [1920, 1080])),
        assets_dir=Path(get("assets_dir", "assets/")),
        char_lim=get("char_lim", 5000),
    )


def _parse_entry(entry: dict) -> tuple[list[Node], list[str]]:
    # One entry can yield several nodes, in the order their keys appear in the entry.
    # Each directive (plugins/producers/*/directive.py) parses its own value + the entry-level keys it declares.
    if not isinstance(entry, dict):
        raise ValueError(f"expected a mapping like '- n: text', got {entry!r}")

    present = []        # (matched alias, directive)
    others = []
    for key in entry:
        directive = DIRECTIVES.get(key)
        if directive is None:
            others.append(key)
            continue
        for prev_key, prev in present:
            if prev is directive:
                raise ValueError(f"{directive.name} given twice ({prev_key!r} and {key!r})")
        present.append((key, directive))

    if not present:
        return [], [f"no directive, entry ignored (keys: {list(entry)})"]

    warnings = []
    for key in others:
        owners = [d.name for _, d in present if key in d.keys]
        if len(owners) > 1:
            raise ValueError(f"{key!r} is ambiguous: read by {' and '.join(owners)} - split them into separate entries")
        if not owners:
            warnings.append(f"unknown key {key!r} ignored")

    nodes = [d.parse(entry[key], entry, key) for key, d in present]
    return nodes, warnings


def _label(entry) -> str:
    if isinstance(entry, dict) and entry:
        key, value = next(iter(entry.items()))
        text = f"{key}: {value}"
    else:
        text = repr(entry)
    return text if len(text) <= 40 else text[:37] + "..."
