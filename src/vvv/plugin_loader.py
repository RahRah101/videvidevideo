"""Plugin discovery via entry points.

Plugins (directives, producers, sources, assemblers) are packages listed under the
`vvv.plugins` entry-point group; importing one runs its register_* calls. vvv's own
plugins are declared in pyproject.toml the same way a third-party package would.
Backends (TTS, stems) are separate groups, loaded lazily by name via load_backend.

Entry points live in installed metadata: after editing pyproject.toml, rerun `pip install -e .`.
"""
from __future__ import annotations
import importlib.metadata
import sys

PLUGIN_GROUP = "vvv.plugins"

_loaded = False


def _entry_points(group: str) -> list[importlib.metadata.EntryPoint]:
    return list(importlib.metadata.entry_points(group=group))


def load_plugins() -> list[str]:
    """Import every installed vvv plugin once. Returns the names that loaded."""
    global _loaded
    eps = _entry_points(PLUGIN_GROUP)
    if not eps:
        raise RuntimeError(
            f"no vvv plugins found (entry-point group {PLUGIN_GROUP!r}). "
            "If you just changed pyproject.toml, rerun `pip install -e .`"
        )
    loaded = []
    for ep in sorted(eps, key=lambda e: e.name):
        try:
            ep.load()
            loaded.append(ep.name)
        except Exception as e:  # a broken plugin must not take vvv down with it
            if not _loaded:
                print(f"[plugins] failed to load {ep.name!r} ({ep.value}): {e}", file=sys.stderr)
    _loaded = True
    return loaded


def backend_names(group: str) -> list[str]:
    """Names in a backend group, from metadata only (nothing imported)."""
    return sorted({ep.name for ep in _entry_points(group)})


def load_backend(group: str, name: str):
    """The backend class registered as `name` in `group`, imported only now."""
    for ep in _entry_points(group):
        if ep.name == name:
            return ep.load()
    raise ValueError(f"unknown {group} backend {name!r}. available: {backend_names(group)}")
