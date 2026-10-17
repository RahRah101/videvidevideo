from __future__ import annotations
from dataclasses import dataclass

from vvv.ir.nodes import Node


@dataclass(frozen=True, slots=True)
class NarrateNode(Node):
    text: str
    voice: str | None = None
    # on_word, effect
