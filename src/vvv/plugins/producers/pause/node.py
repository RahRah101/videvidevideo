from __future__ import annotations
from dataclasses import dataclass

from vvv.ir.nodes import Node


@dataclass(frozen=True, slots=True)
class PauseNode(Node):
    duration_s: float
