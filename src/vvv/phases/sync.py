from __future__ import annotations

from vvv.ir.resolved import ResolvedEntry, TimedEntry
from vvv.context import Context
from vvv.interfaces.sync import SyncProvider
from vvv.registry import register_sync


@register_sync("sequential")
class SequentialSync(SyncProvider):
    """Lays entries end-to-end on the timeline.

    start_s[i] = sum(duration_s[j] for j in 0..i-1)

    This is the v1 sync. v2 will be ElevenLabsTimestampSync with
    word-level cue placement.
    """

    def time(
        self,
        entries: list[ResolvedEntry],
        ctx: Context,
    ) -> list[TimedEntry]:
        timed: list[TimedEntry] = []
        cursor = 0.0
        for entry in entries:
            timed.append(TimedEntry(resolved=entry, start_s=cursor))
            cursor += entry.duration_s
        return timed


#TODO: Implement timestamp/on_word etc... dependent sync using ElevenLabsTimestampSync etc... 
