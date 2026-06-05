"""Plugin registry.

Producers/assemblers/sync providers register themselves at import time
via decorators. The orchestrator looks them up by name when it needs
to dispatch.
"""
from __future__ import annotations
from typing import Type

from vvv.interfaces.producer import Producer
from vvv.interfaces.assembler import Assembler
from vvv.interfaces.sync import SyncProvider


PRODUCERS: dict[type, Type[Producer]] = {}
ASSEMBLERS: dict[str, Type[Assembler]] = {}
SYNC_PROVIDERS: dict[str, Type[SyncProvider]] = {}


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
