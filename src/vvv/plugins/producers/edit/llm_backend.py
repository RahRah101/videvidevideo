"""LLM backend for `e:` edits. Selected by `config: edit: {llm: <name>}`, loaded lazily from the
`vvv.llm_backends` entry-point group; a backend reads its own config section named after its
entry point (e.g. `claude: {model, max_tokens}`)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Image:
    """An image to show the model (e.g. a still of the clip an overlay sits on)."""
    media_type: str      # "image/png"
    data: bytes


@dataclass(frozen=True, slots=True)
class Message:
    role: str                                   # "user" | "assistant"
    text: str
    images: tuple[Image, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int
    output_tokens: int


class LLMBackend(ABC):
    @classmethod
    def from_config(cls, config) -> "LLMBackend":
        """Construct from the script's Config. Raise ValueError for missing keys/settings."""
        return cls()

    def cache_identity(self) -> dict:
        """Everything about this backend that changes its output (backend name, model).
        Goes into the edit's cache key: switching models regenerates, nothing else does."""
        return {"backend": type(self).__name__}

    @property
    def label(self) -> str:
        """Short name for logs and the spend guard, e.g. 'claude-sonnet-5-5'."""
        return type(self).__name__

    @abstractmethod
    def complete(self, system: str, messages: list[Message]) -> tuple[str, Usage]:
        """One paid call. Returns the model's text and token usage. Never retries on its own
        (the producer owns retries, so spend stays visible)."""
        ...
