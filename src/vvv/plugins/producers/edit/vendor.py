"""Third-party files an edit's HTML may use, fetched once (acquisition) and kept in the user cache.
Never shipped in the repo: GSAP is under its own license (https://gsap.com/standard-license).
Pinned by version AND sha256, so a changed upstream file is an error, not a silent swap."""
from __future__ import annotations
import hashlib
import os
import urllib.request
from pathlib import Path

GSAP = {
    "name": "gsap.min.js",
    "url": "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js",
    "sha256": "c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280",
}


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "vvv" / "vendor"


def fetch(spec: dict) -> Path:
    """Path to the cached file; downloads it the first time (the only network use here)."""
    path = cache_dir() / spec["sha256"][:16] / spec["name"]
    if path.exists() and _sha256(path) == spec["sha256"]:
        return path
    print(f"[vendor] downloading {spec['url']} (once)")
    with urllib.request.urlopen(spec["url"], timeout=60) as r:
        data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != spec["sha256"]:
        raise RuntimeError(f"{spec['url']}: sha256 {got} != pinned {spec['sha256']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
