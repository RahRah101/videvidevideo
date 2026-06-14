from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class NarrateNode:
    text: str
    # on_word, effect

@dataclass(frozen=True, slots=True)
class ClipNode:
    source: str
    from_s: float | None = None
    to_s: float | None = None
    duration_s: float | None = None # only meaningful for image. Might be stupid
    keep_audio: bool = True

@dataclass(frozen=True, slots=True)
class PauseNode:
    duration_s: float


#TODO: The fact I have to specify a new stem node in a core file is disgusting.
#The node/parser architecture needs to be more decoupled similar to producers 
#Will have to refactor later.
@dataclass(frozen=True, slots=True)
class StemNode:
    source: str                   
    stems: tuple[str, ...] 
    from_s: float | None = None
    to_s: float | None = None

Node = NarrateNode | ClipNode | PauseNode | StemNode | TitleNode
