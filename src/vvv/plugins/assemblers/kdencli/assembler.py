import re
import subprocess
from pathlib import Path

from vvv.registry import register_assembler
from vvv.interfaces.assembler import Assembler
from vvv.ir.resolved import ResolvedEntry, TimedEntry
from vvv.ir.nodes import Node
from vvv.plugins.producers.clip.node import ClipNode
from vvv.context import Context, Meta


# Path to external tools
# TODO: Use config file
KDENCLI = "kdencli"

# -- Kdencli Helper --
def _kdencli(*args):
    """Run a kdencli command. Prints command, raises on failure."""
    cmd = [KDENCLI] + [str(a) for a in args]
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"kdencli failed ({result.returncode}):\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stderr: {result.stderr.strip()}"
        )
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    return result.stdout

def _kdencli_ts(seconds: float) -> str:
       """Format float seconds as M:SS.mmm or H:MM:SS.mmm for kdencli (TimeUtil::parseTimestamp reads the fraction)."""
       total_ms = int(round(seconds * 1000))
       h, rem = divmod(total_ms, 3_600_000)
       m, ms = divmod(rem, 60_000)
       s = ms / 1000
       if h:
           return f"{h}:{m:02d}:{s:06.3f}"
       return f"{m}:{s:06.3f}"

@register_assembler("kdencli")
class KdencliAssembler(Assembler):
    output_suffix = ".kdenlive"
    # -1 = kdencli picks the first track of the right kind with room at --at (FindOrCreateTrack),
    # creating one if needed. Replaces the old hardcoded VIDEO=0 / TTS=1 / AUDIO=2.
    AUTO_TRACK = "-1"

    def assemble(
        self,
        entries: list[TimedEntry],
        ctx: Context,
        output: Path,
    ) -> Path:
        self._fps = ctx.meta.fps
        self._named_tracks: dict[str, str] = {}   # DSL `track:` name -> kdencli track id, this run only
        self._create_project(output, ctx.meta)
        # track id -> [type, end_s], kept from kdencli's own output; used to find a free audio track
        self._tracks: dict[str, list] = {
            tid: [kind, float(end)]
            for tid, kind, end in re.findall(r"\[(\d+)\] (video|audio) - ([\d.]+)s", _kdencli("info", str(output)))
        }

        for timed in entries:
            self._place(timed, output)

        return output

    def _t(self, seconds: float) -> float:
        # snap to whole frames: kdencli truncates to ms when saving, so unsnapped floats drift
        return round(seconds * self._fps) / self._fps

    def _secs(self, seconds: float) -> str:
        return f"{self._t(seconds):.6f}"

    def _track(self, name: str | None, project: Path, kind: str = "video") -> str:
        if name is None:
            return self.AUTO_TRACK
        if name not in self._named_tracks:
            self._named_tracks[name] = self._add_track(project, kind)
        return self._named_tracks[name]

    def _add_track(self, project: Path, kind: str) -> str:
        out = _kdencli("add-track", str(project), "--type", kind)
        m = re.search(r"Added \w+ track (\d+)", out)
        if not m:
            raise RuntimeError(f"kdencli add-track: unexpected output {out!r}")
        self._tracks[m.group(1)] = [kind, 0.0]
        return m.group(1)

    def _placed(self, out: str, kind: str, timed) -> None:
        # "Placed ... on track N -> entry M": remember where that track now ends
        m = re.search(r"on track (\d+)", out)
        if not m:
            raise RuntimeError(f"kdencli: unexpected output {out!r}")
        end = self._t(timed.start_s + timed.resolved.duration_s)
        t = self._tracks.setdefault(m.group(1), [kind, 0.0])
        t[1] = max(t[1], end)

    def _free_audio_track(self, project: Path, at: float) -> str:
        for tid, (kind, end) in sorted(self._tracks.items(), key=lambda kv: int(kv[0])):
            if kind == "audio" and end <= self._t(at) + 1e-6:
                return tid
        return self._add_track(project, "audio")

    def _cut_args(self, entry) -> list[str]:
        node = entry.node
        if not isinstance(node, ClipNode):
            return []
        args = []
        #TODO: Might need to standardize magic-string contracts like "start_hint". In like a ir/meta_keys.py file or something
        from_s = node.from_s if node.from_s is not None else entry.extras.get("start_hint")
        if from_s is not None:
            args += ["--ss", _kdencli_ts(self._t(from_s))]
        if node.to_s is not None:
            args += ["--to", _kdencli_ts(self._t(node.to_s))]
        return args

    def _create_project(self, output: Path, meta: Meta) -> None:
        _kdencli("create", str(output),
                 "--fps", str(meta.fps),
                 "--width", str(meta.resolution[0]),
                 "--height", str(meta.resolution[1]))

    def _place(self, timed: TimedEntry, project: Path) -> None:
        entry = timed.resolved
        if entry.kind == "audio":
            self._place_audio(entry, timed, project)
        elif entry.kind == "video":
            self._place_video(entry, timed, project)
        elif entry.kind == "image":
            self._place_image(entry, timed, project)
        elif entry.kind == "marker":
            self._place_marker(timed)
        elif entry.kind == "title":
            self._place_title(entry, timed, project)
        else:
            raise RuntimeError(f"unknown kind: {entry.kind}")

    # Every kind is placed at sync's start_s (--at). kdencli inserts the blanks before it,
    # so gaps and pauses land where sync put them.
    def _place_audio(self, entry, timed, project):
        out = _kdencli("place", str(project),
                       "-t", self.AUTO_TRACK,
                       "--file", str(entry.media),
                       "--at", self._secs(timed.start_s),
                       *self._cut_args(entry))
        self._placed(out, "audio", timed)

    def _place_video(self, entry, timed, project):
        common = ["--file", str(entry.media), "--at", self._secs(timed.start_s), *self._cut_args(entry)]
        out = _kdencli("place", str(project), "-t", self.AUTO_TRACK, *common, "--video-only")
        self._placed(out, "video", timed)
        if entry.extras.get("has_audio", False):
            # Split A/V ourselves: kdencli's split pairs with the *nearest* audio track even when
            # it's busy (an `over` clip on top of a clip with sound), and `--audio-only -t -1`
            # picks a video track for a file that has video. TODO: fix in KdenCLI, then drop this.
            track = self._free_audio_track(project, timed.start_s)
            out = _kdencli("place", str(project), "-t", track, *common, "--audio-only")
            self._placed(out, "audio", timed)

    def _place_image(self, entry, timed, project):
        out = _kdencli("place", str(project),
                       "-t", self.AUTO_TRACK,
                       "--file", str(entry.media),
                       "--at", self._secs(timed.start_s),
                       "--length", self._secs(entry.duration_s or 1.0))
        self._placed(out, "video", timed)

    def _place_marker(self, timed):
        # No file to place: pauses only move sync's cursor, and the next entry's --at
        # leaves the gap (kdencli fills it with a blank).
        pass
    def _place_title(self, entry, timed, project):
        node = entry.node          # TitleNode
        s = node.style
        args = ["title", str(project),
                "-t", self._track(node.track, project, "video"),
                "--text", node.text,
                "--at", self._secs(timed.start_s),
                "--duration", self._secs(node.duration_s)]

        # placement: explicit xy overrides anchor
        if node.x is not None and node.y is not None:
            args += ["--xy", "--x", str(node.x), "--y", str(node.y)]
        else:
            args += ["--anchor", node.anchor, "--margin", str(node.margin)]

        args += self._title_style_args(s)
        self._placed(_kdencli(*args), "video", timed)

    def _title_style_args(self, s):
        args = ["--font", s.font, "--font-size", str(s.font_size),
                "--color", s.color, "--outline-color", s.outline_color,
                "--outline", s.outline,
                "--box-width", str(s.box_width), "--box-height", str(s.box_height),
                "--letter-spacing", str(s.letter_spacing),
                "--line-spacing", str(s.line_spacing)]
        if s.bold:      args.append("--bold")
        if s.italic:    args.append("--italic")
        if s.underline: args.append("--underline")
        if s.font_file: args += ["--font-file", s.font_file]
        if s.shadow:    args += ["--shadow", s.shadow]
        if s.gradient:  args += ["--gradient", s.gradient]
        return args
