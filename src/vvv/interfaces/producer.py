from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar

from vvv.ir.nodes import Node
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context


class Producer(ABC):
    """Owns one DSL directive. Turns a Node into a ResolvedEntry.

    Producers carry their own dependencies (TTSBackend, LLMBackend, etc.)
    as constructor args. The core never imports those: composition calls
    `build(config)`, and a producer that needs a backend picks and builds it there.
    """

    node_type: ClassVar[type[Node]]
    # the script's `config:` section this producer reads, if any
    CONFIG_SECTION: ClassVar[str | None] = None

    @classmethod
    def build(cls, config) -> "Producer":
        """Construct for one run from the script's Config. Override when you need backends/settings."""
        return cls()

    @classmethod
    def config_sections(cls) -> set[str]:
        """Config sections this producer may read (for unknown-section warnings). Metadata only."""
        return {cls.CONFIG_SECTION} if cls.CONFIG_SECTION else set()

    @abstractmethod
    def produce(self, node: Node, ctx: Context) -> ResolvedEntry:
        ...
