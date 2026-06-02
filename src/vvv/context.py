from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Meta:
    title: str
    voice_id: str
    fps: int
    resolution: tuple[int, int]
    assets_dir: Path
    char_lim: int = 5000


@dataclass(frozen=True, slots=True)
class Context:
    """State that flows through resolve/sync/assemble phases.

    DOES NOT carry backend instances. NEVER REWRITE IT TO DO SO.
    Each producer owns its own backends as constructor args. The orchestrator stays
    ignorant of whether any given producer uses TTS / LLM / nothing.
    """
    meta: Meta
    work_dir: Path
