"""Content-addressed file cache shared by producers.

key = cache_key(kind, **inputs)      # inputs = everything that changes the output
path = Cache(dir).get_or_make(key, make, prefix="narrate_001", suffix=".mp3")

A cache hit is any file in `dir` named `*_<key><suffix>`, so the human-readable prefix
can change (e.g. a line moved) without losing the hit. `make(tmp)` writes to a temp
file that is renamed into place only when it returns, so an interrupted run never
leaves a broken file that looks cached.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

KEY_LEN = 16
_TMP = ".tmp"


def cache_key(kind: str, **inputs: Any) -> str:
    """Hash of canonical JSON, so field boundaries can't blur ("ab"+"c" != "a"+"bc")."""
    blob = json.dumps({"kind": kind, **inputs}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:KEY_LEN]


class Cache:
    def __init__(self, root: Path):
        self.root = Path(root)

    def find(self, key: str, suffix: str = "") -> Path | None:
        if not self.root.is_dir():
            return None
        hits = sorted(
            p for p in self.root.glob(f"*_{key}{suffix}")
            if not p.name.endswith(f"{_TMP}{suffix}")
        )
        return hits[0].resolve() if hits else None

    def path_for(self, key: str, prefix: str, suffix: str = "") -> Path:
        return (self.root / f"{prefix}_{key}{suffix}").resolve()

    def get_or_make(self, key: str, make: Callable[[Path], Any], prefix: str, suffix: str = "") -> Path:
        hit = self.find(key, suffix)
        if hit is not None:
            return hit
        self.root.mkdir(parents=True, exist_ok=True)
        out = self.path_for(key, prefix, suffix)
        # keep the real extension last: ffmpeg & co pick the format from it
        tmp = out.with_name(f"{prefix}_{key}{_TMP}{suffix}")
        tmp.unlink(missing_ok=True)
        try:
            make(tmp)
            if not tmp.exists():
                raise RuntimeError(f"cache make() for {out.name} wrote nothing")
            tmp.replace(out)
        finally:
            tmp.unlink(missing_ok=True)
        return out
