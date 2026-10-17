from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from vvv.ir.resolved import TimedEntry
from vvv.context import Context


class Assembler(ABC):
    # default output file extension, e.g. ".kdenlive" (cli: build/<slug><output_suffix>)
    output_suffix: ClassVar[str] = ""
    # the script's `config:` section this assembler reads, if any
    CONFIG_SECTION: ClassVar[str | None] = None

    @classmethod
    def build(cls, config) -> "Assembler":
        """Construct for one run from the script's Config."""
        return cls()

    @classmethod
    def config_sections(cls) -> set[str]:
        return {cls.CONFIG_SECTION} if cls.CONFIG_SECTION else set()

    @abstractmethod
    def assemble(
        self,
        entries: list[TimedEntry],
        ctx: Context,
        output: Path,
    ) -> Path:
        ...
