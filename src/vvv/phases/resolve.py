from __future__ import annotations
from dataclasses import replace

from vvv.ir.resolved import ResolvedEntry, TimedEntry
from vvv.ir.placement import Placement
from vvv.ir.timeline import TimelineView
from vvv.ir.nodes import Node
from vvv.context import Context
from vvv.interfaces.producer import Producer

def resolve(nodes: list[Node],
            producers: dict[type, Producer],
            ctx: Context,
            placements: list[Placement] | None = None) -> list[ResolvedEntry]:
    # placements runs parallel to nodes (ParsedScript.placements); None = all default
    placements = placements or [Placement()] * len(nodes)
    out: list[ResolvedEntry] = []
    for node, placement in zip(nodes, placements, strict=True):
        producer = producers.get(type(node))
        if producer is None:
            raise RuntimeError(f"no producer for {type(node).__name__}")
        # timeline-aware producers only declare a placeholder now; resolve_timed fills it after sync
        entry = producer.declare(node, ctx) if producer.needs_timeline else producer.produce(node, ctx)
        out.append(replace(entry, placement=placement))
    return out


def resolve_timed(timed: list[TimedEntry],
                  producers: dict[type, Producer],
                  ctx: Context) -> list[TimedEntry]:
    """Pass 2, after sync: produce every timeline-aware entry with a TimelineView of its slot.

    Returns the same list with those placeholders replaced (same start_s, same placement).
    Entries from ordinary producers pass through untouched.
    """
    resolved_entries: list[TimedEntry] = list(timed)    # untouched entries stay the same objects
    for i, view in timeline_views(timed, producers, ctx).items():
        t = timed[i]
        producer = producers[type(t.resolved.node)]
        duration = view.duration_s
        result = producer.produce_timed(t.resolved.node, ctx, view)

        if(abs(result.duration_s - duration) > (1 / ctx.meta.fps)):
            raise ValueError(f"{type(t.resolved.node).__name__} at {t.start_s:.3f}s: produced "
                 f"{result.duration_s:.3f}s, expected {duration:.3f}s")
        resolved_entries[i] = TimedEntry(
            resolved=replace(result, placement=t.resolved.placement),
            start_s=t.start_s)
    return resolved_entries


def timeline_views(timed: list[TimedEntry],
                   producers: dict[type, Producer],
                   ctx: Context) -> dict[int, TimelineView]:
    """The TimelineView of every timeline-aware entry, keyed by its index in `timed`.
    Shared by resolve_timed and the cli's spend guard (paid_work needs the view too)."""
    views: dict[int, TimelineView] = {}

    # Helper for readability
    def at(j): return timed[j] if j is not None else None

    for i, t in enumerate(timed):
        # Find the producer associated with the timed entry
        producer = producers[type(t.resolved.node)]

        # The producer does not need timeline information: no view
        if not producer.needs_timeline:
            continue

        over = t.resolved.placement.over
        base = _nonover(timed, i - 1, -1) if over else None               # index of the base (over entries only)
        if over:
            assert base is not None, "over on the first entry" 
        anchor = base if over else i
        prev = _nonover(timed, anchor - 1, -1)             # index of prev, or None
        nxt = _nonover(timed, i + 1, +1)                  # index of next, or none
        duration = 0.0
        if over and t.resolved.duration_s == 0.0:
            duration = timed[base].resolved.duration_s
        else:
            duration = t.resolved.duration_s

        views[i] = TimelineView(start_s=t.start_s, duration_s=duration,
                    base=at(base), prev=at(prev), next=at(nxt),
                    fps=ctx.meta.fps, resolution=ctx.meta.resolution)
    return views

def _nonover(timed: list[TimedEntry], start: int, step: int):
    """First non-over entry from index `start`, moving by `step` (-1 left, +1 right). None if none."""
    stop = None
    if step == -1:
        stop = -1
    elif step == 1:
        stop = len(timed)
    else:
        raise ValueError("step can only be 1 or -1")

    for i in range(start, stop, step):
        if not timed[i].resolved.placement.over:
            return i
    return None

