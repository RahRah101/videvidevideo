"""Renderer backend for `e:` edits: turns the folder the LLM wrote into a clip. Selected by
`config: edit: {renderer: <name>}`, loaded lazily from the `vvv.edit_renderers` group.
HyperFrames first; Remotion etc. plug in the same way."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path


class EditRenderer(ABC):
    @classmethod
    def from_config(cls, config) -> "EditRenderer":
        return cls()

    def cache_identity(self) -> dict:
        """What changes a render besides the source itself (renderer name/version, settings)."""
        return {"renderer": type(self).__name__}

    @abstractmethod
    def contract(self) -> str:
        """Authoring rules for the LLM: file layout, timing attributes, what is forbidden.
        This is the renderer-specific half of the system prompt."""
        ...

    @abstractmethod
    def prepare(self, project_dir: Path) -> None:
        """Make the folder renderable before the LLM's file lands in it (vendored libs, media/)."""
        ...

    @abstractmethod
    def lint(self, project_dir: Path) -> list[str]:
        """Errors that would make the render fail or lie. Empty list = OK. Warnings don't count."""
        ...

    @abstractmethod
    def render(self, project_dir: Path, output: Path, alpha: bool, fps: int) -> Path:
        """Render to `output` (offline). alpha=True: transparent background (overlays)."""
        ...

    @property
    def entry_file(self) -> str:
        """The file the LLM writes inside the project folder."""
        return "index.html"

    @property
    def output_suffix_alpha(self) -> str:
        return ".mov"

    @property
    def output_suffix(self) -> str:
        return ".mp4"
