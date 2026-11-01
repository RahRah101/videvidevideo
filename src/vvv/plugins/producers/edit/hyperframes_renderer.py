"""HyperFrames as the `e:` renderer. Entry point `hyperframes` in `vvv.edit_renderers`.
Reads the same `hyperframes:` config section as the hyperframes assembler (cli)."""
from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from vvv.plugins.assemblers.hyperframes import hfcli
from . import vendor
from .contract import HYPERFRAMES_CONTRACT
from .renderer_backend import EditRenderer


class HyperframesRenderer(EditRenderer):
    def __init__(self, cli: list[str] | None = None):
        found = hfcli.find_cli(cli)
        if found is None:
            raise ValueError("hyperframes renderer: `hyperframes` CLI not found "
                             "(set config: hyperframes: {cli: [...]})")
        self.cli: list[str] = found
        self._version: str | None = None

    @classmethod
    def from_config(cls, config) -> "HyperframesRenderer":
        return cls(cli=hfcli.parse_cli(hfcli.read_section(config).get("cli")))

    def cache_identity(self) -> dict:
        # settings that change the pixels; the CLI version too, since a new version may render differently
        # the contract is the system prompt: editing it must regenerate the edits it shaped
        contract = hashlib.sha256(self.contract().encode()).hexdigest()[:12]
        return {"renderer": "hyperframes", "version": self.version, "frames": "png", "contract": contract}

    @property
    def version(self) -> str:
        if self._version is None:
            r = hfcli.run(self.cli, ["--version"], Path.cwd())
            self._version = (r.stdout.strip() or r.stderr.strip()).splitlines()[-1] if r.returncode == 0 else "unknown"
        return self._version

    def contract(self) -> str:
        return HYPERFRAMES_CONTRACT

    def prepare(self, project_dir: Path) -> None:
        media = project_dir / "media"
        media.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(vendor.fetch(vendor.GSAP), media / vendor.GSAP["name"])

    def lint(self, project_dir: Path) -> list[str]:
        r = hfcli.run(self.cli, ["lint"], project_dir)
        if r.returncode == 0:
            return []
        report = (r.stdout + r.stderr).strip()
        # keep the finding lines (errors and their fixes); fall back to the whole report
        lines = [ln.strip() for ln in report.splitlines() if ln.strip().startswith(("✗", "Fix:"))]
        return lines or [report]

    def render(self, project_dir: Path, output: Path, alpha: bool, fps: int) -> Path:
        self._warn_untagged_color(project_dir / "media")
        args = ["render", "-o", str(output), "--fps", str(fps), "--video-frame-format", "png", "--quiet"]
        if alpha:
            args += ["--format", "mov"]          # ProRes 4444 with alpha
        r = hfcli.run(self.cli, args, project_dir)
        if r.returncode != 0 or not output.exists():
            raise RuntimeError(f"hyperframes render failed for {project_dir}:\n{(r.stdout + r.stderr).strip()[-2000:]}")
        return output

    @staticmethod
    def _warn_untagged_color(media_dir: Path) -> None:
        # untagged sources make the browser guess BT.601 vs BT.709: a visible color seam when spliced
        for f in sorted(media_dir.iterdir()) if media_dir.is_dir() else []:
            if f.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm"):
                continue
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=color_space", "-of", "json", str(f)],
                               capture_output=True, text=True)
            streams = json.loads(r.stdout or "{}").get("streams") or [{}]
            if streams[0].get("color_space") in (None, "unknown"):
                print(f"[edit] warning: {f.name} has no color tags; colors may shift at the splice")
