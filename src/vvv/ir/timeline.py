from __future__ import annotations
from dataclasses import dataclass

from vvv.ir.resolved import TimedEntry


@dataclass(frozen=True, slots=True)
class TimelineView:
    """What a timeline-aware producer sees of its slot (pass 2, after sync). Plain data, read-only.

    start_s / duration_s: the slot this entry fills. For an `over:` entry without its own duration
                          this is the base's duration (it lasts as long as what it sits on).
    base:   for an `over:` entry, the non-over entry it sits on; None otherwise.
    prev / next: the nearest non-over entries before / after the slot (for an `over:` entry:
                 before / after its base). Overlays are never neighbours. None at the edges.
    """
    start_s: float
    duration_s: float
    base: TimedEntry | None
    prev: TimedEntry | None
    next: TimedEntry | None
    fps: int
    resolution: tuple[int, int]
