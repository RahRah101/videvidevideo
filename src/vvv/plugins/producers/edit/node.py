from __future__ import annotations
from dataclasses import dataclass

from vvv.ir.nodes import Node


@dataclass(frozen=True, slots=True)
class EditNode(Node):
    """`e:` - an edit written by an LLM from a natural-language prompt, rendered to a clip.

    duration_s: None = last as long as the entry it sits on (`over:` only).
    take:       re-roll counter; a different take is a different cache entry.
    revise:     notes applied in order on top of the previous version (each one = 1 LLM call).
    """
    prompt: str
    duration_s: float | None = None
    take: int = 1
    revise: tuple[str, ...] = ()
