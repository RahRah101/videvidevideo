from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path

from vvv.plugin_loader import backend_names, load_backend


class StemSeparator(ABC):
    """Swappable backend that splits an audio file into stems.

    Peer of TTSBackend. StemProducer depends on THIS, never on a concrete
    backend, so the choice of backend is a config decision (`config: stem: backend:`).
    """

    @classmethod
    def from_config(cls, config) -> "StemSeparator":
        """Build from the script's Config; a backend's section is named after its entry point."""
        return cls()

    @abstractmethod
    def separate(self, audio: Path, stems: list[str], output_dir: Path) -> dict[str, Path]:
        """Split `audio` into the requested `stems`.

        Returns {stem_name: path_to_stem_file}, one entry per requested stem.
        """
        ...


# Generic backend discovery: every backend (demucs included) is an entry point in this group.
ENTRY_POINT_GROUP = "vvv.stem_backends"


def available_backends() -> list[str]:
    return backend_names(ENTRY_POINT_GROUP)


def get_backend_class(name: str) -> type[StemSeparator]:
    return load_backend(ENTRY_POINT_GROUP, name)
