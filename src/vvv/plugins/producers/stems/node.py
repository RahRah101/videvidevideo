from __future__ import annotations
from dataclasses import dataclass

from vvv.ir.nodes import Node


@dataclass(frozen=True, slots=True)
class StemNode(Node):
    source: str
    stems: tuple[str, ...]
    from_s: float | None = None
    to_s: float | None = None
