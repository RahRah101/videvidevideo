from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class NarrateNode:
    text: str
    # on_word, effect

@dataclass(frozen=True, slots=True)
class ClipNode:
    source: str           # raw, unresolved (could be path or URL)
    from_s: float | None = None
    to_s: float | None = None

@dataclass(frozen=True, slots=True)
class PauseNode:
    duration_s: float

Node = NarrateNode | ClipNode | PauseNode
