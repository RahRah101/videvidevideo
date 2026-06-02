from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

from vvv.ir.resolved import TimedEntry
from vvv.context import Context


class Assembler(ABC):
    @abstractmethod
    def assemble(
        self,
        entries: list[TimedEntry],
        ctx: Context,
        output: Path,
    ) -> Path:
