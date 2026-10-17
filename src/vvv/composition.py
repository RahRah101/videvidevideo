"""Builds one run's producers, sync provider and assembler from the registries + the script's config.

Imports no concrete plugin: plugins register themselves (vvv.plugin_loader), and each class
builds itself from config (`build(config)`), picking its own backends. Producers are built
fresh per run, and only for node types the script actually uses.
"""
from __future__ import annotations

from vvv.config import Config
from vvv.interfaces.producer import Producer
from vvv.interfaces.sync import SyncProvider
from vvv.interfaces.assembler import Assembler
from vvv.registry import PRODUCERS, ASSEMBLERS, SYNC_PROVIDERS
import vvv.phases.sync  # registers the core "sequential" sync provider

ASSEMBLE_SECTION = "assemble"      # core-owned: `assemble: { target: <name> }`
DEFAULT_TARGET = "kdencli"
DEFAULT_SYNC = "sequential"


def build_producers(config: Config, needed: set[type]) -> dict[type, Producer]:
    missing = sorted(t.__name__ for t in needed if t not in PRODUCERS)
    if missing:
        raise ValueError(f"no producer registered for {missing} (is its plugin installed?)")
    return {t: PRODUCERS[t].build(config) for t in needed}


def assembler_target(config: Config, override: str | None = None) -> str:
    section = config.section(ASSEMBLE_SECTION, {"target"})
    return override or str(section.get("target", DEFAULT_TARGET))


def build_assembler(config: Config, target: str) -> Assembler:
    if target not in ASSEMBLERS:
        raise ValueError(f"unknown assembler target {target!r}. available: {sorted(ASSEMBLERS)}")
    return ASSEMBLERS[target].build(config)


def build_sync(config: Config) -> SyncProvider:
    return SYNC_PROVIDERS[DEFAULT_SYNC]()


def known_config_sections() -> set[str]:
    """Every section an installed component may read (metadata only, nothing gets built)."""
    known = {ASSEMBLE_SECTION}
    for cls in [*PRODUCERS.values(), *ASSEMBLERS.values()]:
        known |= cls.config_sections()
    return known
