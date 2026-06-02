from __future__ import annotations
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from vvv.ir.nodes import Node


MediaKind = Literal["audio", "video", "image", "marker"]


@dataclass(frozen=True, slots=True)
class ResolvedEntry:
    node: Node
    media: Path | None              # None for marker-kind entries
    kind: MediaKind
    duration_s: float
    # backend-specific stuff, like say timing data returned by ElevenLabs API
    extras: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TimedEntry:
    resolved: ResolvedEntry
    start_s: float
