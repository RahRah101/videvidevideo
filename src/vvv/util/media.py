from __future__ import annotations
from dataclasses import dataclass, field
import json
import subprocess
from pathlib import Path
import os
import re
import urllib.request
import urllib.parse
from vvv.interfaces.source import SourceHandler
from vvv.registry import SOURCE_HANDLERS
from vvv.context import Context
from vvv.interfaces.source import SourceInfo

# Path to external tools
# TODO: Use config file
YTDLP = "yt-dlp"
FFPROBE = "ffprobe"
FFMPEG = "ffmpeg"

def probe_duration(filepath):
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json",
         "-show_format", str(filepath)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {filepath}: {result.stderr}")
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])
def download_video_media(url, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # TODO: you would want to find a way for the user the specify
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

def download_image_media(url, output_dir):
    #one line... seriously? Is this even needed as a function?
    #are you dumb?
    urllib.request.urlretrieve(url, output_dir)

def is_image(url):
    #another one line function that might not deserve to live
    return re.search(r"\.(jpg|jpeg|png|gif|webp)$", url)

def is_url(path: str) -> bool:
       return bool(re.match(r"https?://", path))

def download_image_media(url: str, output_dir: str) -> str:
       Path(output_dir).mkdir(parents=True, exist_ok=True)
       filename = Path(urllib.parse.urlparse(url).path).name or "image"
       out_path = Path(output_dir) / filename
       urllib.request.urlretrieve(url, str(out_path))
       return str(out_path)

def has_audio_stream(filepath: str | Path) -> bool:
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(filepath)],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def concat(parts: list[Path], output: Path) -> Path:
    listfile = output.with_suffix(".txt")
    with open(listfile, "w") as f:
        for part in parts:
            f.write(f"file '{Path(part).resolve()}'\n")
    result = subprocess.run(
        [FFMPEG, "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", "-y", str(output)],
        capture_output=True, text=True
    )
    listfile.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return output

def resolve_media(source: str, ctx: Context) -> SourceInfo:
    source = str(source).strip()

    for handler in SOURCE_HANDLERS:
        if handler.handles(source):
            return handler.resolve(source, ctx)
    p = Path(source)
    if not p.is_absolute():
        p = Path(ctx.meta.assets_dir) / p
    if not p.exists():
        raise FileNotFoundError(f"Media not found: {p}")
    return SourceInfo(path=p.resolve())