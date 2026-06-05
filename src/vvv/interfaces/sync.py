from __future__ import annotations
from abc import ABC, abstractmethod

from vvv.ir.resolved import ResolvedEntry, TimedEntry
from vvv.context import Context


class SyncProvider(ABC):
    @abstractmethod
    def time(
        self,
        entries: list[ResolvedEntry],
        ctx: Context,
    ) -> list[TimedEntry]:
        ...
