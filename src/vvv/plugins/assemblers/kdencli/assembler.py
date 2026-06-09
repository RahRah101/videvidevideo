import subprocess
from pathlib import Path

from vvv.registry import register_assembler
from vvv.interfaces.assembler import Assembler
from vvv.ir.resolved import ResolvedEntry, TimedEntry
from vvv.ir.nodes import Node, ClipNode
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
       """Format float seconds as M:SS or H:MM:SS for kdencli."""
       total = int(round(seconds))
       h, rem = divmod(total, 3600)
       m, s = divmod(rem, 60)
       if h:
           return f"{h}:{m:02d}:{s:02d}"
       return f"{m}:{s:02d}"

@register_assembler("kdencli")
class KdencliAssembler(Assembler):
    VIDEO_TRACK = "0"
    TTS_TRACK = "1"
    AUDIO_TRACK = "2"

    def assemble(
        self,
        entries: list[TimedEntry],
        ctx: Context,
        output: Path,
    ) -> Path:
        self._create_project(output, ctx.meta)

        for timed in entries:
            self._place(timed, output)

        return output

    def _create_project(self, output: Path, meta: Meta) -> None:
        _kdencli("create", str(output),
                 "--fps", str(meta.fps),
                 "--width", str(meta.resolution[0]),
                 "--height", str(meta.resolution[1]))

    def _place(self, timed: TimedEntry, project: Path) -> None:
        entry = timed.resolved
        if entry.kind == "audio":
            self._place_audio(entry, project)
        elif entry.kind == "video":
            self._place_video(entry, timed, project)
        elif entry.kind == "image":
            self._place_image(entry, project)
        elif entry.kind == "marker":
            self._place_marker(timed)
        else:
            raise RuntimeError(f"unknown kind: {entry.kind}")

    #TODO: Shouldn't be TTS track. Like if we want to put the music etc... Change the whole logic of how the assembler understands tracks
    def _place_audio(self, entry, project):
        _kdencli("place", str(project),
                 "-t", self.TTS_TRACK,
                 "--file", str(entry.media),
                 "--audio-only")

    def _place_video(self, entry, timed, project):
        args = ["place", str(project), "-t", self.VIDEO_TRACK,
                "--file", str(entry.media),
        ]
        node = entry.node
        if isinstance(node, ClipNode):
            if node.from_s is not None:
                args += ["--ss", _kdencli_ts(node.from_s)]
            if node.to_s is not None:
                args += ["--to", _kdencli_ts(node.to_s)]
        if not entry.extras.get("has_audio", False):
            args += ["--video-only"]
        _kdencli(*args)

    def _place_image(self, entry, project):
        _kdencli("place", str(project),
                 "-t", self.VIDEO_TRACK,
                 "--file", str(entry.media),
                 "--length", str(entry.duration_s))

    def _place_marker(self, timed):
        # No file to place. Pauses contribute to the timeline cursor
        # but don't get a clip. Future: insert a blank/gap if kdencli
        # adds support.
        pass
