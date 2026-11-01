from __future__ import annotations
from typing import Any

from vvv.registry import register_directive
from vvv.interfaces.directive import Directive
from vvv.util.dsl import pick
from .node import EditNode


def _parse_edit(value: Any, entry: dict, matched_key: str) -> EditNode:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"prompt: expected non-empty text, got {value!r}")

    d = pick(entry, "duration", "d")

    if d is None:
        if not entry.get("over"):
            raise ValueError("full-frame edits need d: (or use over: true to last as long as the clip under it)")
        duration = None
    else:
        try:
            duration = float(d)
        except (TypeError, ValueError):
            raise ValueError(f"d: expected seconds, got {d!r}") from None
        if not duration > 0:
            raise ValueError(f"d: duration should be longer than 0 seconds, got {d!r}")

    take = entry.get("take", 1)
    # bool is a subclass of int: `take: yes` must not pass as take 1
    if not isinstance(take, int) or isinstance(take, bool) or take < 1:
        raise ValueError(f"take: expected a whole number >= 1, got {take!r}")

    revise = entry.get("revise", ())
    if isinstance(revise, str):
        revise = (revise,)
    if not isinstance(revise, (list, tuple)) or not all(isinstance(r, str) and r.strip() for r in revise):
        raise ValueError(f"revise: expected a note or a list of non-empty notes, got {revise!r}")

    return EditNode(prompt=value.strip(), duration_s=duration, take=take, revise=tuple(revise))



register_directive(Directive(
    "edit", ("e", "edit"), _parse_edit,
    frozenset({"d", "duration", "take", "revise"}),
))
