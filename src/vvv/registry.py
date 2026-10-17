"""Plugin registry.

Plugins register themselves at import time (vvv.plugin_loader imports every
`vvv.plugins` entry point). DIRECTIVES -> parse, SOURCE_HANDLERS -> resolve_media
(sorted by priority), PRODUCERS / ASSEMBLERS / SYNC_PROVIDERS -> composition.py,
which calls each class's build(config). Backends (TTS, stems) are not registered
here: they are entry-point groups loaded lazily by name (plugin_loader.load_backend).
"""
from __future__ import annotations
from typing import Type

from vvv.interfaces.producer import Producer
from vvv.interfaces.assembler import Assembler
from vvv.interfaces.sync import SyncProvider
from vvv.interfaces.source import SourceHandler
from vvv.interfaces.directive import Directive


PRODUCERS: dict[type, Type[Producer]] = {}
ASSEMBLERS: dict[str, Type[Assembler]] = {}
SYNC_PROVIDERS: dict[str, Type[SyncProvider]] = {}
SOURCE_HANDLERS: list[SourceHandler] = []
# alias -> Directive ("n" and "narrate" both map to the narrate directive)
DIRECTIVES: dict[str, Directive] = {}

def register_source(h: SourceHandler) -> None:
    # kept sorted by priority so load order (entry points) doesn't decide who wins
    SOURCE_HANDLERS.append(h)
    SOURCE_HANDLERS.sort(key=lambda s: s.priority)

def register_directive(d: Directive) -> Directive:
    for alias in d.aliases:
        if alias in DIRECTIVES and DIRECTIVES[alias] is not d:
            raise ValueError(f"directive alias {alias!r} already taken by {DIRECTIVES[alias].name!r}")
        DIRECTIVES[alias] = d
    return d

def register_producer(cls: Type[Producer]) -> Type[Producer]:
    if not hasattr(cls, "node_type"):
        raise TypeError(f"{cls.__name__} must set `node_type` ClassVar")
    PRODUCERS[cls.node_type] = cls
    return cls

def register_assembler(name: str):
    def deco(cls: Type[Assembler]) -> Type[Assembler]:
        ASSEMBLERS[name] = cls
        return cls
    return deco


def register_sync(name: str):
    def deco(cls: Type[SyncProvider]) -> Type[SyncProvider]:
        SYNC_PROVIDERS[name] = cls
        return cls
    return deco