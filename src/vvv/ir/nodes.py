from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class NarrateNode:
    text: str
    voice: str | None = None
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

@dataclass(frozen=True, slots=True)
class TitleStyle:
    font: str = "Liberation Sans"
    font_size: int = 50
    color: str = "255,255,255,255"
    outline_color: str = "0,0,0,255"
    outline: str = "2"
    bold: bool = False
    italic: bool = False
    underline: bool = False
    letter_spacing: int = 0
    line_spacing: int = 0
    box_width: int = 0
    box_height: int = 0
    font_file: str | None = None
    shadow: str | None = None
    gradient: str | None = None

@dataclass(frozen=True, slots=True)
class TitleNode:
    text: str
    anchor: str = "bottom-center"
    margin: int = 80
    x: int | None = None          # None = use anchor; set = explicit xy
    y: int | None = None
    track: str | None = None      # named track, or None = auto
    duration_s: float = 5.0
    style: TitleStyle = field(default_factory=TitleStyle)


Node = NarrateNode | ClipNode | PauseNode | StemNode | TitleNode
