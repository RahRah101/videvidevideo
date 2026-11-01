from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar, TYPE_CHECKING

from vvv.ir.nodes import Node
from vvv.ir.resolved import ResolvedEntry
from vvv.context import Context

if TYPE_CHECKING:
    from vvv.ir.timeline import TimelineView


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

    # -- timeline-aware producers (two-pass resolve) ------------------------------
    # A producer whose output depends on its place in the timeline (what it sits on, its
    # neighbours) sets needs_timeline = True. Pass 1 (before sync) calls declare(); pass 2
    # (after sync) calls produce_timed() with a TimelineView. Its duration must be known in
    # pass 1 (declared, or inherited from the base via `over:`), so pass 2 never moves anything.
    needs_timeline: ClassVar[bool] = False

    def declare(self, node: Node, ctx: Context) -> ResolvedEntry:
        """Pass 1 placeholder: media=None, the declared duration (0.0 for `over:` without one)."""
        raise NotImplementedError(f"{type(self).__name__} sets needs_timeline but has no declare()")

    def produce_timed(self, node: Node, ctx: Context, view: "TimelineView") -> ResolvedEntry:
        """Pass 2: the real entry. Its duration_s must equal view.duration_s."""
        raise NotImplementedError(f"{type(self).__name__} sets needs_timeline but has no produce_timed()")

    def paid_work(self, node: Node, ctx: Context, view: "TimelineView | None" = None) -> list[str]:
        """One short line per paid call producing this node would make right now (cache misses),
        e.g. ["edit 3: LLM call (claude-sonnet-5-5)"]. The cli refuses to spend without --yes.
        view is given for timeline-aware producers, None otherwise."""
        return []
