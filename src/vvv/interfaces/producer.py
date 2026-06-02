from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar

from vvv.ir.nodes import Node
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context


class Producer(ABC):
    """Owns one DSL directive. Turns a Node into a ResolvedEntry.

    Producers carry their own dependencies (TTSBackend, LLMBackend, etc.)
    as constructor args. The core never imports those.
    """

    directive: ClassVar[str]

    @abstractmethod
    def produce(self, node: Node, ctx: Context) -> ResolvedEntry:
        #TODO: Implement this
