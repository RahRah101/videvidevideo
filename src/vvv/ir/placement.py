from __future__ import annotations
from dataclasses import dataclass

# entry keys read by the core, valid next to any directive (directives can't claim them)
PLACEMENT_KEYS = ("over",)


@dataclass(frozen=True, slots=True)
class Placement:
    """Where an entry sits on the timeline, from core entry keys (not the directive's).

    over: start with the previous non-over entry instead of after it, and don't push
          the timeline forward (a title or second layer over a clip).
    """
    over: bool = False
