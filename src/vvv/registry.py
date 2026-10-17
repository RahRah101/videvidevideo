"""Plugin registry.

Producers/assemblers/sync providers register themselves at import time
via decorators. SOURCE_HANDLERS (resolve_media) and DIRECTIVES (parse) are used for dispatch.
PRODUCERS is read by `--list-producers` only; ASSEMBLERS and SYNC_PROVIDERS
are not read yet. composition.py does the real wiring, because producers
need injected backends (planned fix: build(config) factories, see TODO.md).
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
    SOURCE_HANDLERS.append(h)

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