from __future__ import annotations
from dataclasses import dataclass

from vvv.ir.nodes import Node


@dataclass(frozen=True, slots=True)
class ClipNode(Node):
    source: str
    from_s: float | None = None
    to_s: float | None = None
    duration_s: float | None = None # only meaningful for image. Might be stupid
    keep_audio: bool = True
