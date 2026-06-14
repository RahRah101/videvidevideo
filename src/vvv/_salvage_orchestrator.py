import os
import re
import json
import subprocess
from pathlib import Path
from elevenlabs import ElevenLabs


# Path to external tools
# TODO: Use config file
KDENCLI = "kdencli"
YTDLP = "yt-dlp"
FFPROBE = "ffprobe"

# --- MEDIA HELPERS ---
def probe_duration(filepath):
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json",
         "-show_format", filepath],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {filepath}: {result.stderr}")
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])

def is_url(path):
    return bool(re.match(r'https?://', str(path)))


def download_media(url, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # TODO: Realize that yt-dlp downloads
    # videos, and not images. What if the user
    # wants to download an image to include as a clip?
    # Also you would want to find a way for the user the specify
    # download parameters (quality etc...) potentially in the DSL
    # How would you do that?
    result = subprocess.run(
        [YTDLP, "--restrict-filenames", "--no-overwrites",
         "-o", f"{output_dir}/%(id)s.%(ext)s",
         "--print", "after_move:filepath",
         url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed on {url}: {result.stderr}")
    #print final filepath
    return result.stdout.strip().split('\n')[-1]

def resolve_media(path, assets_dir, download_dir):
    """
    Resolve a media reference to a local filepath.
    - URLs -> download via yt-dlp, and then return the resulting filepath
    - Relative paths -> prepend assets_dir
    - Absolute paths -> use as-is
    """
    path = str(path).strip()

    if is_url(path):
        print(f"  [download] {path}")
        return download_media(path, download_dir)

    p = Path(path)
    if not p.is_absolute():
        p = Path(assets_dir) / p

    if not p.exists():
        raise FileNotFoundError(f"Media not found: {p}")

    return str(p.resolve())

# --- External tools helpers ---
# -- TTS stuff --
# TODO: For now this will assume ElevenLabs. Makes this more modular later
def generate_tts(text, voice_id, output_path):
    """
    Generate narration audio via ElevenLabs.
    Requires ELEVEN_API_KEY env var.
    Returns path to the generated .mp3 file.
    """

    api_key = os.environ.get("ELEVEN_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set ELEVEN_API_KEY environment variable. "
            "Get one at https://elevenlabs.io"
        )

    client = ElevenLabs(api_key=api_key)

    audio_iter = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
    )

    with open(output_path, "wb") as f:
        for chunk in audio_iter:
            f.write(chunk)

    return output_path

# -- Kdencli Helper --
def kdencli(*args):
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

# --- Text operations helpers ---
def auto_split(text, char_lim):
    # TODO : Implement auto-split
    pass


class Orchestrator:
    """
    V1 orchestrator: YAML entries -> TTS API calls + kdencli commands -> .kdenlive project.

    Behavior:
    - narrate entries: ElevenLabs TTS API call -> audio file -> place on audio track
    - clip entries: resolve path (yt-dlp if URL) -> place on video track
    - image entries: resolve path -> place on video track (default 1s)
    - edit/text_overlay: TODO

    All clips are placed sequentially via kdencli place (appends to track).
    """

    # kdencli create produces: track 0 = video, track 1 = audio
    VIDEO_TRACK = "0"
    TTS_TRACK = "1"
    AUDIO_TRACK = "2"
    DEFAULT_IMAGE_DURATION_S = 1

    def __init__(self, meta, entries, build_dir="build"):
        self.meta = meta
        self.entries = entries
        self.build_dir = Path(build_dir)
        self.audio_dir = self.build_dir / "audio"
        self.media_dir = self.build_dir / "media"

        title = meta.get("title", "project")
        slug = re.sub(r'[^\w\-]', '_', title.lower()).strip('_')[:50]
        self.project_path = self.build_dir / f"{slug}.kdenlive"
        
        self.fps = meta.get("fps", 30)
        self.voice_id = meta.get("voice_id", "")
        self.assets_dir = meta.get("assets_dir", "assets/")
        self.char_lim = meta.get("char_lim", 5000)
        self.resolution = meta.get("resolution", [1920, 1080])

        # counters for naming output files
        self.narration_count = 0
        self.clip_count = 0

        # stats
        self._stats = {"tts": 0, "clips": 0, "images": 0, "skipped": []}

    def run(self):
        print(f"\n{'='*60}")
        print(f"  videvidevideo V1")
        print(f"  \"{self.meta.get('title', 'Untitled')}\"")
        print(f"  {self.resolution[0]}x{self.resolution[1]} @ {self.fps}fps")
        print(f"{'='*60}\n")

        self._setup_dirs()
        self._create_project()

        for i, entry in enumerate(self.entries):
            self._process(entry, i)

        self._print_summary()
        return str(self.project_path)

    def _setup_dirs(self):
        for d in [self.build_dir, self.audio_dir, self.media_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _create_project(self):
        print("Creating a new Kdenlive project...")
        kdencli("create", str(self.project_path),
                "--fps", str(self.fps),
                "--width", str(self.resolution[0]),
                "--height", str(self.resolution[1]))

    def _process(self, entry, index):
        if "narrate" in entry:
            self._handle_narrate(entry)
        elif "clip" in entry:
            self._handle_clip(entry)
        elif "image" in entry:
            self._handle_image(entry)
        elif "pause" in entry:
            self._handle_pause(entry)
        elif "text_overlay" in entry:
            # TODO: implement text overlay
            self._skip("text_overlay", entry.get("text_overlay", ""))
        elif "edit" in entry:
            #TODO: implement edit orchestration
            self._skip("edit", entry.get("edit", "")[:60])
        else:
            self._skip("unknown", str(entry)[:60])

    def _handle_narrate(self, entry):
        text = entry["narrate"]
        self.narration_count += 1
        chunk_name = f"chunk_{self.narration_count:03d}.mp3"
        output_path = str(self.audio_dir / chunk_name)

        # truncate display text
        display = text[:70] + ("..." if len(text) > 70 else "")
        print(f"\n[tts #{self.narration_count}] \"{display}\"")

        # guard: ElevenLabs char limit
        if len(text) > self.char_lim:
            print(f"Text exceeds char_lim ({len(text)} > {self.char_lim})")
            print(f"    Split this narration entry in YAML.")
            # TODO: auto-split

        generate_tts(text, self.voice_id, output_path)

        # verify the file was created and has content
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"TTS output empty or missing: {output_path}")

        duration = probe_duration(output_path)
        print(f"{chunk_name} ({duration:.1f}s)")

        # place on audio track, kdencli appends sequentially
        kdencli("place", str(self.project_path),
                "-t", self.TTS_TRACK,
                "--file", output_path)

        self._stats["tts"] += 1

    def _handle_clip(self, entry):
        self.clip_count += 1
        path = resolve_media(
            entry["clip"], self.assets_dir, str(self.media_dir)
        )

        args = ["place", str(self.project_path),
                "-t", self.VIDEO_TRACK,
                "--file", path]

        # timestamp range(KDENCLI expects HH:MM:SS / MM:SS / SS format)
        if "from" in entry:
            args += ["--ss", str(entry["from"])]
        if "to" in entry:
            args += ["--to", str(entry["to"])]

        clip_label = Path(path).name
        ts_info = ""
        if "from" in entry and "to" in entry:
            ts_info = f" [{entry['from']}s–{entry['to']}s]"
        print(f"\n[clip #{self.clip_count}] {clip_label}{ts_info}")

        kdencli(*args)
        self._stats["clips"] += 1

    def _handle_image(self, entry):
        self.clip_count += 1
        path = resolve_media(
            entry["image"], self.assets_dir, str(self.media_dir)
        )

        length = self.DEFAULT_IMAGE_DURATION_S

        print(f"\n[image #{self.clip_count}] {Path(path).name} "
              f"({self.DEFAULT_IMAGE_DURATION_S}s)")

        kdencli("place", str(self.project_path),
                "-t", self.VIDEO_TRACK,
                "--file", path,
                "--length", str(length))

        self._stats["images"] += 1

    def _handle_pause(self, entry):
        duration = entry["pause"]
        print(f"\n[pause] {duration}s  adjust manually in Kdenlive")
        # kdencli doesn't have a blank/gap command yet
        # in V2 this would insert a blank element on both tracks

    def _skip(self, entry_type, detail):
        print(f"\n[skip] {entry_type}: \"{detail}\" (Feature not yet supported)")
        self._stats["skipped"].append(entry_type)

    # -- Summary --
    def _print_summary(self):
        print(f"\n{'─'*60}")
        print(f"  Done.")
        print(f"  TTS chunks generated: {self._stats['tts']}")
        print(f"  Clips placed:         {self._stats['clips']}")
        print(f"  Images placed:        {self._stats['images']}")
        if self._stats["skipped"]:
            print(f"  Skipped entries:      {len(self._stats['skipped'])} "
                  f"({', '.join(self._stats['skipped'])})")
        print(f"\n  Project: {self.project_path}")
        print(f"You can now open in Kdenlive, sync video to narration, and export, fck nigga.")
        print(f"{'─'*60}\n")

# --- Public facing API function -- 
def orchestrate(meta, entries, build_dir="build"):
    """
    Orchestrate the generation of a project.

    Args:
        meta: expanded metadata dict from parser
        entries: list of expanded script entries from parser
        build_dir: output directory (default: "build")

    Returns:
        Path to the generated .kdenlive file
    """
    orch = Orchestrator(meta, entries, build_dir)
    return orch.run()
