"""Per-project config from the script's top-level `config:` block.

    config:
      narrate:    { adopt_legacy: true }
      elevenlabs: { model_id: eleven_multilingual_v2 }

Plain data only (never backend instances). Components read their own section at
build time via `section(name, keys)`, so composition.py never learns a section's keys.
Secrets (API keys) stay in env vars, never here.
Later: merge a global config file under this (TODO.md > Config layer).
"""
from __future__ import annotations
from typing import Any


class Config:
    def __init__(self, raw: dict | None = None):
        raw = raw or {}
        if not isinstance(raw, dict):
            raise ValueError(f"config: must be a mapping of sections, got {raw!r}")
        for name, body in raw.items():
            if not isinstance(body, dict):
                raise ValueError(f"config.{name}: must be a mapping, got {body!r}")
        self._raw = raw
        self._used: set[str] = set()
        self.warnings: list[str] = []

    def section(self, name: str, keys: set[str]) -> dict[str, Any]:
        """The `name` section (empty if absent). Warns on keys not in `keys`."""
        self._used.add(name)
        body = dict(self._raw.get(name) or {})
        for key in sorted(set(body) - keys):
            self.warnings.append(f"config.{name}: unknown key {key!r} ignored")
            body.pop(key)
        return body

    def unused_sections(self) -> list[str]:
        """Call after everything is built: sections nobody read (typos, removed plugins)."""
        return [f"config: unknown section {name!r} ignored" for name in self._raw if name not in self._used]
