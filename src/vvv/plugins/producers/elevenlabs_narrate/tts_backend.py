from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

class TTSBackend(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice_id: str, output: Path) -> Path:
        """Write audio of `text` to `output`. Return the written path."""
        ...

    @classmethod
    def from_config(cls, config) -> "TTSBackend":
        """Build from the script's Config; a backend's section is named after its entry point."""
        return cls()

    def cache_identity(self) -> dict:
        """Everything about this backend that changes the audio (goes into the cache key).
        Override to add model/version/settings."""
        return {"backend": type(self).__name__}
