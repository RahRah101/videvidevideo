from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import importlib.metadata


class StemSeparator(ABC):
    """Swappable backend that splits an audio file into stems.

    Peer of TTSBackend. StemProducer depends on THIS, never on a concrete
    backend, so the choice of backend is a composition decision.
    """

    @abstractmethod
    def separate(self, audio: Path, stems: list[str], output_dir: Path) -> dict[str, Path]:
        """Split `audio` into the requested `stems`.

        Returns {stem_name: path_to_stem_file}, one entry per requested stem.
        """
        ...


# Generic backend discovery
_ENTRY_POINT_GROUP = "vvv.stem_backends"


def available_backends() -> dict[str, type[StemSeparator]]:
    from .demucs_backend import LocalDemucs
    backends: dict[str, type[StemSeparator]] = {"demucs": LocalDemucs}

    try:
        eps = importlib.metadata.entry_points(group=_ENTRY_POINT_GROUP)
    except TypeError:  # Python <3.10 entry_points() API
        eps = importlib.metadata.entry_points().get(_ENTRY_POINT_GROUP, [])

    for ep in eps:
        backends[ep.name] = ep.load()
    return backends


def get_backend(name: str) -> StemSeparator:
    backends = available_backends()
    if name not in backends:
        raise ValueError(
            f"unknown stem backend '{name}'. available: {sorted(backends)}"
        )
    return backends[name]()