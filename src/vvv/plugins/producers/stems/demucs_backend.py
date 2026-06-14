from __future__ import annotations
import subprocess
from pathlib import Path
from .stem_backend import StemSeparator

_DEMUCS_STEMS = {"vocals", "drums", "bass", "other"}

# TODO: Implement local demucs use
class LocalDemucs(StemSeparator):
    def __init__(self, model: str = "htdemucs"):
        self.model = model

    def separate(self, audio: Path, stems: list[str], output_dir: Path) -> dict[str, Path]:
        ...