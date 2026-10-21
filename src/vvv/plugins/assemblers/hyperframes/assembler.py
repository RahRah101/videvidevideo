"""HyperFrames assembler: timed entries -> a HyperFrames project folder (index.html + media/).

vvv owns this folder's index.html and media/ and rewrites them on every build; hand/agent
work belongs elsewhere (TODO Phase 2). Render/preview is the HyperFrames CLI's job.
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

from vvv.registry import register_assembler
from vvv.interfaces.assembler import Assembler
from vvv.ir.resolved import TimedEntry
from vvv.ir.ids import element_ids
from vvv.plugins.producers.clip.node import ClipNode
from vvv.context import Context
from vvv.util.cache import cache_key


@register_assembler("hyperframes")
class HyperframesAssembler(Assembler):
    output_suffix = ".hf"          # a project folder, not a file
    CONFIG_SECTION = "hyperframes"
    CONFIG_KEYS = {"cli", "lint"}

    def __init__(self, cli: list[str] | None = None, lint: bool = True):
        self.cli = cli
        self.lint = lint

    @classmethod
    def build(cls, config) -> "HyperframesAssembler":
        sec = config.section(cls.CONFIG_SECTION, cls.CONFIG_KEYS)
        # cli: a path or an argv list, e.g. [~/.local/node22/bin/node, .../bin/hyperframes] when
        # the default `node` is older than HyperFrames needs. Unset: `hyperframes` on PATH.
        cli = sec.get("cli")
        if isinstance(cli, str):
            cli = [cli]
        if cli is not None and not (isinstance(cli, list) and all(isinstance(a, str) for a in cli)):
            raise ValueError(f"hyperframes.cli: expected a path or a list of strings, got {cli!r}")
        cli = [os.path.expanduser(a) for a in cli] if cli else None
        return cls(cli=cli, lint=bool(sec.get("lint", True)))

    def assemble(self, entries: list[TimedEntry], ctx: Context, output: Path) -> Path:
        try:
            import jinja2
        except ImportError:
            raise RuntimeError("the hyperframes target needs jinja2: pip install 'videvidevideo[hyperframes]'") from None
        if output.exists() and not output.is_dir():
            raise RuntimeError(f"{output} exists and is not a folder (the hyperframes target writes a project folder)")

        self._fps = ctx.meta.fps
        self._out = output
        (output / "media").mkdir(parents=True, exist_ok=True)
        self._linked: set[str] = set()
        self._fonts: dict[str, dict] = {}

        elements = self._layout(entries)
        end = max((self._t(t.start_s + t.resolved.duration_s) for t in entries), default=0.0)

        env = jinja2.Environment(loader=jinja2.FileSystemLoader(Path(__file__).parent),
                                 autoescape=True, keep_trailing_newline=True)
        html = env.get_template("index.html.j2").render(
            script_name=ctx.meta.title, width=ctx.meta.resolution[0], height=ctx.meta.resolution[1],
            fps=self._fps, duration=self._n(end), elements=elements, fonts=list(self._fonts.values()))
        (output / "index.html").write_text(html, encoding="utf-8")

        for f in (output / "media").iterdir():       # media from earlier builds that nothing uses now
            if f.name not in self._linked:
                f.unlink()

        if self.lint:
            self._run_lint(output)
        return output

    # -- timing -----------------------------------------------------------------
    def _t(self, seconds: float) -> float:
        # whole frames, like kdencli: HF works in seconds, integer frames avoid drift
        return round(seconds * self._fps) / self._fps

    def _n(self, seconds: float) -> str:
        return f"{self._t(seconds):.6f}".rstrip("0").rstrip(".") or "0"

    # -- layout -----------------------------------------------------------------
    def _layout(self, entries: list[TimedEntry]) -> list[dict]:
        """One element per entry. Lanes = first lane free at the entry's start (the same rule as
        kdencli's -t -1); a title's `track:` name gets its own lane. Visual lane = paint order
        (z-index), since HF's data-track-index is a Studio display lane the render ignores."""
        ids = element_ids([t.resolved.node for t in entries])
        visual: list[float] = []          # lane -> end_s
        audio: list[float] = []
        named: dict[str, int] = {}
        placed = []
        for timed, el_id in zip(entries, ids):
            entry = timed.resolved
            if entry.kind == "marker":
                continue
            start, end = self._t(timed.start_s), self._t(timed.start_s + entry.duration_s)
            name = getattr(entry.node, "track", None) if entry.kind == "title" else None
            if entry.kind == "audio":
                lane = self._free_lane(audio, start)
                audio[lane] = end
            elif name is not None:
                if name not in named:
                    named[name] = len(visual)
                    visual.append(float("inf"))        # reserved: auto placement never uses it
                lane = named[name]
            else:
                lane = self._free_lane(visual, start)
                visual[lane] = end
            placed.append((timed, el_id, entry.kind == "audio", lane))

        out = []
        for timed, el_id, is_audio, lane in placed:
            el = self._element(timed, el_id)
            el["track"] = len(visual) + lane if is_audio else lane
            el["z"] = lane
            out.append(el)
        return out

    @staticmethod
    def _free_lane(lanes: list[float], start: float) -> int:
        for i, end in enumerate(lanes):
            if end <= start + 1e-6:
                return i
        lanes.append(0.0)
        return len(lanes) - 1

    def _element(self, timed: TimedEntry, el_id: str) -> dict:
        entry = timed.resolved
        el = {"id": el_id, "start": self._n(timed.start_s), "duration": self._n(entry.duration_s)}
        if entry.kind == "title":
            node = entry.node
            return {**el, "tag": "title", "text": node.text, "css": self._title_css(node)}
        el["src"] = self._link(entry.media)
        if entry.kind == "image":
            return {**el, "tag": "img"}
        el["media_start"] = self._media_start(entry)
        if entry.kind == "audio":
            return {**el, "tag": "audio"}
        if entry.kind == "video":
            return {**el, "tag": "video", "has_audio": entry.extras.get("has_audio", False)}
        raise RuntimeError(f"hyperframes: unsupported kind {entry.kind!r}")

    def _media_start(self, entry) -> str | None:
        # same cut as kdencli's --ss: only clips carry one (narration/stems are already cut files)
        if not isinstance(entry.node, ClipNode):
            return None
        from_s = entry.node.from_s if entry.node.from_s is not None else entry.extras.get("start_hint")
        return self._n(from_s) if from_s else None

    def _link(self, path: Path) -> str:
        """Hardlink (or copy) a media file into media/: the render's browser only serves the project folder."""
        path = Path(path).resolve()
        st = path.stat()
        key = cache_key("hf-media", path=str(path), size=st.st_size, mtime=st.st_mtime_ns)
        name = f"{path.stem}_{key}{path.suffix}"
        dest = self._out / "media" / name
        if not dest.exists():
            try:
                os.link(path, dest)
            except OSError:                  # other filesystem / no hardlinks
                shutil.copy2(path, dest)
        self._linked.add(name)
        return f"media/{name}"

    # -- titles -----------------------------------------------------------------
    def _title_css(self, node) -> str:
        s = node.style
        family = s.font
        if s.font_file:
            src = self._link(Path(s.font_file).expanduser())
            family = f"vvv-font-{Path(src).stem}"
            self._fonts[src] = {"family": family, "src": src}
        css = [f'font-family: "{family}", sans-serif',
               f"font-size: {s.font_size}px",
               f"color: {_rgba(s.color)}",
               f"font-weight: {'bold' if s.bold else 'normal'}",
               f"font-style: {'italic' if s.italic else 'normal'}",
               f"letter-spacing: {s.letter_spacing}px",
               f"line-height: calc(1.3em + {s.line_spacing}px)"]
        if s.underline:
            css.append("text-decoration: underline")
        if float(s.outline or 0) > 0:
            css += [f"-webkit-text-stroke: {float(s.outline) * 2:g}px {_rgba(s.outline_color)}",
                    "paint-order: stroke fill"]        # stroke centered on the edge, fill on top: outer outline
        if s.box_width:
            css.append(f"width: {s.box_width}px")
        if s.box_height:
            css.append(f"height: {s.box_height}px")
        if s.shadow:
            css.append(_shadow_css(s.shadow))
        if s.gradient:
            css += _gradient_css(s.gradient)
        return "; ".join(c for c in css if c) + "; " + self._position_css(node)

    @staticmethod
    def _position_css(node) -> str:
        if node.x is not None and node.y is not None:
            return f"left: {node.x}px; top: {node.y}px"
        vert, _, horiz = node.anchor.partition("-")
        if node.anchor == "center":
            vert, horiz = "center", "center"
        elif not horiz:
            horiz = "center"
        m = node.margin
        tx = ty = "0"
        css = []
        if horiz == "left":
            css += [f"left: {m}px", "text-align: left"]
        elif horiz == "right":
            css += [f"right: {m}px", "text-align: right"]
        else:
            css += ["left: 50%", "text-align: center"]; tx = "-50%"
        if vert == "top":
            css.append(f"top: {m}px")
        elif vert == "bottom":
            css.append(f"bottom: {m}px")
        else:
            css.append("top: 50%"); ty = "-50%"
        css.append(f"transform: translate({tx}, {ty})")
        return "; ".join(css)

    # -- lint -------------------------------------------------------------------
    def _run_lint(self, project: Path) -> None:
        found = shutil.which("hyperframes")
        cli = self.cli or ([found] if found else None)
        if cli is None:
            print("[hyperframes] warning: `hyperframes` CLI not found, lint skipped "
                  "(set config: hyperframes: {cli: ...} or lint: false)")
            return
        result = subprocess.run([*cli, "lint"], cwd=project, capture_output=True, text=True,
                                env={**os.environ, "NO_COLOR": "1"})
        report = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise RuntimeError(f"hyperframes lint failed for {project}:\n{report}")
        print(f"[hyperframes] lint: {report.splitlines()[-1] if report else 'ok'}")


# TitleStyle carries kdenlive-style values (colors "r,g,b,a", shadow/gradient strings);
# translated to CSS here. TODO: a backend-neutral title style when a 3rd assembler needs it.
def _rgba(rgba: str) -> str:
    r, g, b, a = (int(v) for v in rgba.split(","))
    return f"rgba({r}, {g}, {b}, {a / 255:.3g})"


def _argb_hex(c: str) -> str:
    """'#AARRGGBB' -> css rgba()."""
    c = c.lstrip("#")
    if len(c) != 8:
        raise ValueError(f"expected #AARRGGBB, got {c!r}")
    a, r, g, b = (int(c[i:i + 2], 16) for i in range(0, 8, 2))
    return f"rgba({r}, {g}, {b}, {a / 255:.3g})"


def _shadow_css(shadow: str) -> str:
    # kdenlive: "enabled;#AARRGGBB;blur;offX;offY"
    try:
        enabled, color, blur, x, y = shadow.split(";")
        if enabled.strip() in ("0", "false"):
            return ""
        return f"text-shadow: {int(x)}px {int(y)}px {int(blur)}px {_argb_hex(color)}"
    except ValueError as e:
        raise ValueError(f"title style shadow {shadow!r}: expected 'enabled;#AARRGGBB;blur;offX;offY' ({e})") from None


def _gradient_css(gradient: str) -> list[str]:
    # kdenlive: "#AARRGGBB;#AARRGGBB;startPct;endPct;angle" (angle convention approximated)
    try:
        c1, c2, p1, p2, angle = gradient.split(";")
        bg = f"linear-gradient({int(angle) + 90}deg, {_argb_hex(c1)} {int(p1)}%, {_argb_hex(c2)} {int(p2)}%)"
    except ValueError as e:
        raise ValueError(f"title style gradient {gradient!r}: expected '#AARRGGBB;#AARRGGBB;0;100;angle' ({e})") from None
    return [f"background: {bg}", "-webkit-background-clip: text", "background-clip: text", "color: transparent"]
