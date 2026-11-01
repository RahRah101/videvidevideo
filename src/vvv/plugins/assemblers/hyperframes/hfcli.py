"""The `hyperframes:` config section and the CLI lookup, shared by the hyperframes assembler and
the hyperframes edit renderer (plugins/producers/edit). One section, one key set."""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

CONFIG_SECTION = "hyperframes"
CONFIG_KEYS = {"cli", "lint"}


def read_section(config) -> dict:
    return config.section(CONFIG_SECTION, CONFIG_KEYS)


def parse_cli(value) -> list[str] | None:
    """`cli:` is a path or an argv list, e.g. [~/.local/node22/bin/node, .../bin/hyperframes]
    when the default `node` is older than HyperFrames needs. None = `hyperframes` on PATH."""
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if not (isinstance(value, list) and value and all(isinstance(a, str) for a in value)):
        raise ValueError(f"hyperframes.cli: expected a path or a list of strings, got {value!r}")
    return [os.path.expanduser(a) for a in value]


def find_cli(cli: list[str] | None) -> list[str] | None:
    if cli:
        return cli
    found = shutil.which("hyperframes")
    return [found] if found else None


def run(cli: list[str], args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([*cli, *args], cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, "NO_COLOR": "1"})
