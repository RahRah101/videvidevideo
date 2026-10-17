"""Helpers shared by directive parsers (plugins/producers/*/directive.py). Raise ValueError on bad input."""
from __future__ import annotations
from typing import Any

from vvv.util.timestamps import TIMESTAMP_RANGE, parse_timestamp


def pick(entry: dict, *aliases: str, default: Any = None) -> Any:
    """Value of whichever alias is present (e.g. "duration" / "d"). Two at once is an error."""
    present = [a for a in aliases if a in entry]
    if len(present) > 1:
        raise ValueError(f"{' and '.join(present)} both given - use one")
    return entry[present[0]] if present else default


def split_source_range(value: Any, entry: dict) -> tuple[str, float | None, float | None]:
    """'clip.mp4 [1:01-1:06]' or 'clip.mp4' + entry-level from:/to: -> (source, from_s, to_s)."""
    if isinstance(value, (dict, list)):
        raise ValueError(f"expected a source string, got a {type(value).__name__}")
    source = str(value).strip()
    from_s = to_s = None

    inline = TIMESTAMP_RANGE.search(source)
    if inline:
        source = source[:inline.start()].strip()
        from_s, to_s = parse_timestamp(inline.group(1)), parse_timestamp(inline.group(2))

    if "from" in entry or "to" in entry:
        if inline:
            raise ValueError("range given twice: inline [..] and from:/to:")
        from_s = parse_timestamp(entry["from"]) if "from" in entry else None
        to_s = parse_timestamp(entry["to"]) if "to" in entry else None

    if from_s is not None and to_s is not None and to_s <= from_s:
        raise ValueError(f"range ends ({to_s}s) before it starts ({from_s}s)")
    return source, from_s, to_s
