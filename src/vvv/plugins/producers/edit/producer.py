"""`e:` producer: an LLM writes a composition from the prompt + what the edit sits on, a renderer
turns it into a clip. Timeline-aware : it needs its slot, its base and its neighbours.

Two caches, so each step only reruns when its own inputs change:
  edits/edit_NNN_<html key>/index.html   key = prompt, take, revisions, LLM, renderer, context
  edits/edit_NNN_<render key>.mov|.mp4   key = the HTML's CONTENT, renderer, alpha, fps
A hand-edited index.html therefore only re-renders; it never calls the LLM.
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from vvv.registry import register_producer
from vvv.interfaces.producer import Producer
from vvv.ir.resolved import ResolvedEntry, TimedEntry
from vvv.ir.timeline import TimelineView
from vvv.context import Context
from vvv.plugin_loader import backend_names, load_backend
from vvv.plugins.producers.clip.node import ClipNode
from vvv.util.cache import Cache, cache_key
from vvv.util.media import probe_duration
from .node import EditNode
from .llm_backend import LLMBackend, Message, Image
from .renderer_backend import EditRenderer

STILLS = (0.1, 0.5, 0.9)          # where to grab frames of the footage under an overlay
STILL_WIDTH = 960


@dataclass
class EditContext:
    """Everything the LLM is told about the slot, plus what goes into the project's media/."""
    alpha: bool                                     # overlay (transparent) vs full-frame
    request: str                                    # the text part of the first user message
    images: list[Image] = field(default_factory=list)
    media: dict[str, Path] = field(default_factory=dict)    # name in media/ -> source file
    digest: str = ""                                # identity of all of the above, for the cache key


@register_producer
class EditProducer(Producer):
    node_type = EditNode
    needs_timeline = True
    CONFIG_SECTION = "edit"
    CONFIG_KEYS = {"llm", "renderer", "retries"}
    LLM_GROUP = "vvv.llm_backends"
    RENDERER_GROUP = "vvv.edit_renderers"

    @classmethod
    def build(cls, config) -> "EditProducer":
        sec = config.section(cls.CONFIG_SECTION, cls.CONFIG_KEYS)
        retries = sec.get("retries", 1)
        if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
            raise ValueError(f"config.edit.retries: a whole number >= 0, got {retries!r}")
        llm = load_backend(cls.LLM_GROUP, str(sec.get("llm", "claude"))).from_config(config)
        renderer = load_backend(cls.RENDERER_GROUP, str(sec.get("renderer", "hyperframes"))).from_config(config)
        return cls(llm, renderer, retries)

    @classmethod
    def config_sections(cls) -> set[str]:
        return {cls.CONFIG_SECTION, *backend_names(cls.LLM_GROUP), *backend_names(cls.RENDERER_GROUP)}

    def __init__(self, llm: LLMBackend, renderer: EditRenderer, retries: int = 1):
        self.llm = llm
        self.renderer = renderer
        self.retries = retries
        self._counter = 0            # human-readable names only; identity is the content key

    # -- the two passes ------------------------------------------------------------
    def produce(self, node, ctx):
        raise RuntimeError("EditProducer is timeline-aware: resolve calls declare() / produce_timed()")

    def declare(self, node: EditNode, ctx: Context) -> ResolvedEntry:
        return ResolvedEntry(node=node, media=None, kind="video",
                             duration_s=node.duration_s or 0.0, extras={"has_audio": False})

    def produce_timed(self, node: EditNode, ctx: Context, view: TimelineView) -> ResolvedEntry:
        self._counter += 1
        name = f"edit_{self._counter:03d}"
        info = self._context(node, ctx, view)
        system = self.renderer.contract()

        # revision chain: level 0 is the prompt alone, level k applies revise[k-1] to level k-1
        project = None
        for level in range(len(node.revise) + 1):
            key = self._html_key(node, info, level)
            previous = (project / self.renderer.entry_file).read_text() if project else None
            note = node.revise[level - 1] if level else None
            project = self._cached_dir(ctx, key, f"{name}_r{level}",
                                       lambda d, prev=previous, n=note: self._make_project(d, info, system, prev, n))

        html = (project / self.renderer.entry_file).read_bytes()
        rkey = cache_key("edit_render", html=hashlib.sha256(html).hexdigest(),
                         renderer=self.renderer.cache_identity(), alpha=info.alpha, fps=view.fps)
        suffix = self.renderer.output_suffix_alpha if info.alpha else self.renderer.output_suffix
        out = Cache(ctx.work_dir / "edits").get_or_make(
            rkey, lambda tmp: self.renderer.render(project, tmp, info.alpha, view.fps), prefix=name, suffix=suffix)
        return ResolvedEntry(node=node, media=out, kind="video", duration_s=probe_duration(out),
                             extras={"has_audio": False})

    def paid_work(self, node: EditNode, ctx: Context, view: TimelineView | None = None) -> list[str]:
        if view is None:
            return []
        info = self._context(node, ctx, view, images=False)
        missing = [lvl for lvl in range(len(node.revise) + 1)
                   if Cache(ctx.work_dir / "edits").find(self._html_key(node, info, lvl)) is None]
        what = node.prompt if len(node.prompt) <= 50 else node.prompt[:47] + "..."
        # a retry after a lint error is extra; the guard lists the minimum
        return [f"edit at {view.start_s:.2f}s ({what!r}): LLM call ({self.llm.label})"
                + (f", revision {lvl}" if lvl else "") for lvl in missing]

    # -- one project folder ----------------------------------------------------------
    def _make_project(self, project_dir: Path, info: EditContext, system: str,
                      previous_html: str | None, note: str | None) -> None:
        self.renderer.prepare(project_dir)
        for target, source in info.media.items():
            _link(source, project_dir / "media" / target)
        messages = [Message("user", info.request, tuple(info.images))]
        if previous_html is not None:
            messages += [Message("assistant", previous_html),
                         Message("user", f"Revise the composition: {note}\nReturn the full updated file.")]
        self._write_valid_html(project_dir, system, messages)

    def _write_valid_html(self, project_dir: Path, system: str, messages: list[Message]) -> None:
        """Get HTML from the LLM, write it, lint it. On lint errors, show them to the LLM and ask
        again, at most self.retries more times. Raise if it is still invalid: only valid HTML may be
        cached (the caller renames the folder into the cache only when this returns)."""
        target = project_dir / self.renderer.entry_file
        for attempt in range(self.retries + 1):
            html = self._ask(system, messages)
            target.write_text(html, encoding="utf-8")
            errors = self.renderer.lint(project_dir)
            if not errors:
                return
            print(f"[edit] lint found {len(errors)} problem(s) (attempt {attempt + 1}/{self.retries + 1})")
            # new list, never the caller's: the model sees what it wrote and exactly what failed
            messages = messages + [
                Message("assistant", html),
                Message("user", "The renderer's lint rejected this file:\n" + "\n".join(errors)
                        + "\nFix these problems and return the full corrected file."),
            ]
        raise RuntimeError(f"edit still invalid after {self.retries + 1} attempt(s):\n" + "\n".join(errors))


    def _ask(self, system: str, messages: list[Message]) -> str:
        """One paid call. Returns the HTML (tolerates a stray ``` fence) and prints the usage."""
        text, usage = self.llm.complete(system, messages)
        print(f"[edit] {self.llm.label}: {usage.input_tokens} in / {usage.output_tokens} out tokens")
        fenced = re.search(r"```(?:html)?\s*\n(.*?)```", text, re.S)
        return (fenced.group(1) if fenced else text).strip() + "\n"

    def _cached_dir(self, ctx: Context, key: str, prefix: str, make) -> Path:
        """Like Cache.get_or_make, for a folder: built in a temp folder, renamed in when complete."""
        root = ctx.work_dir / "edits"
        hit = Cache(root).find(key)
        if hit is not None and hit.is_dir():
            return hit
        root.mkdir(parents=True, exist_ok=True)
        out = root / f"{prefix}_{key}"
        tmp = root / f"{prefix}_{key}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        try:
            make(tmp)
            tmp.replace(out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return out.resolve()

    # -- what the LLM is told ----------------------------------------------------------
    def _html_key(self, node: EditNode, info: EditContext, level: int) -> str:
        return cache_key("edit_html", prompt=node.prompt, take=node.take, revise=list(node.revise[:level]),
                         llm=self.llm.cache_identity(), renderer=self.renderer.cache_identity(),
                         context=info.digest)

    def _context(self, node: EditNode, ctx: Context, view: TimelineView, images: bool = True) -> EditContext:
        w, h = view.resolution
        alpha = view.base is not None
        lines = [f"Request: {node.prompt}",
                 f"Kind: {'overlay (transparent background, composited over footage)' if alpha else 'full-frame'}",
                 f"DURATION={view.duration_s:.3f} FPS={view.fps} WIDTH={w} HEIGHT={h}"]
        info = EditContext(alpha=alpha, request="")
        identity: dict = {"alpha": alpha, "duration": round(view.duration_s, 3), "fps": view.fps, "size": [w, h]}

        if alpha:
            src = _source(view.base)
            if src is not None:
                identity["base"] = src.identity
                lines.append(f"Underneath: {src.describe()}. The attached images are frames of it "
                             f"at {', '.join(f'{int(f * 100)}%' for f in STILLS)} of this edit.")
                if images:
                    info.images = src.stills(view.duration_s)
        else:
            for role, entry in (("prev", view.prev), ("next", view.next)):
                src = _source(entry)
                if src is None:
                    continue
                target = f"{role}{src.path.suffix.lower()}"
                info.media[target] = src.path
                identity[role] = src.identity
                when = "right before" if role == "prev" else "right after"
                lines.append(f"media/{target}: the {src.kind} that plays {when} this edit; {src.describe(role)}.")
        info.request = "\n".join(lines)
        info.digest = cache_key("edit_context", **identity)
        return info


@dataclass
class _Source:
    """The media of a neighbouring/base entry and where it is cut."""
    path: Path
    kind: str            # video | image
    start: float         # source time where the entry starts playing
    duration: float

    @property
    def identity(self) -> dict:
        st = self.path.stat()
        return {"path": str(self.path), "size": st.st_size, "mtime": st.st_mtime_ns,
                "start": round(self.start, 3), "duration": round(self.duration, 3)}

    def describe(self, role: str = "base") -> str:
        if self.kind == "image":
            return f"a still image ({self.path.name})"
        end = self.start + self.duration
        if role == "prev":
            return f"it stopped at source time {end:.3f}s (later footage is usable as a handle)"
        if role == "next":
            return f"it starts at source time {self.start:.3f}s (earlier footage is usable as a handle)"
        return f"video {self.path.name} playing source {self.start:.3f}s-{end:.3f}s"

    def stills(self, edit_duration: float) -> list[Image]:
        span = min(edit_duration, self.duration)
        times = [0.0] if self.kind == "image" else [self.start + f * span for f in STILLS]
        out = []
        for t in times:
            args = ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(self.path), "-frames:v", "1",
                    "-vf", f"scale={STILL_WIDTH}:-2", "-f", "image2pipe", "-c:v", "png", "-"]
            r = subprocess.run(args, capture_output=True)
            if r.returncode == 0 and r.stdout:
                out.append(Image("image/png", r.stdout))
        return out


def _source(entry: TimedEntry | None) -> _Source | None:
    if entry is None or entry.resolved.media is None or entry.resolved.kind not in ("video", "image"):
        return None
    node, r = entry.resolved.node, entry.resolved
    start = 0.0
    if isinstance(node, ClipNode):
        start = node.from_s if node.from_s is not None else (r.extras.get("start_hint") or 0.0)
    return _Source(Path(r.media), r.kind, start, r.duration_s)


def _link(source: Path, dest: Path) -> None:
    if dest.exists():
        return
    try:
        os.link(source, dest)
    except OSError:
        shutil.copy2(source, dest)
