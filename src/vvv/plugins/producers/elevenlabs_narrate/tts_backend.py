from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

class TTSBackend(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice_id: str, output: Path) -> Path:
        """Write audio of `text` to `output`. Return the written path."""
        ...
